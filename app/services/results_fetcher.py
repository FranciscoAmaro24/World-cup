"""
Auto-results fetcher.

Primary source  : ESPN API (no API key needed)
Secondary source: football-data.org (set FOOTBALL_DATA_API_KEY env var)

Runs as an asyncio background task every POLL_INTERVAL seconds.
Also exposes `fetch_now(db)` for the manual admin trigger.
"""
import asyncio
import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("RESULTS_POLL_SECONDS", "300"))  # 5 min default

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
WC_START  = date(2026, 6, 11)
WC_END    = date(2026, 7, 19)

FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_URL = "https://api.football-data.org/v4/competitions/WC/matches"

# ESPN abbreviation → our DB team code (only entries that differ)
ESPN_TO_CODE: dict[str, str] = {
    "SCOT": "SCO",
}

STAGE_REACHED = {
    "group": 0, "r32": 1, "r16": 2, "qf": 3, "sf": 4, "final": 5, "winner": 6,
}

# Knockout round start boundaries (UTC) from the ESPN tournament calendar. Each round
# transitions at 07:00Z, so a match just after midnight UTC (e.g. a late-night kickoff in
# the Americas) still belongs to the previous round — comparing full datetimes, not just
# dates, keeps those on the correct side of the boundary.
_ROUND_DATES = [
    (datetime(2026, 6, 11, 0, 0), "group"),
    (datetime(2026, 6, 28, 7, 0), "r32"),
    (datetime(2026, 7, 4, 7, 0),  "r16"),
    (datetime(2026, 7, 9, 7, 0),  "qf"),
    (datetime(2026, 7, 14, 7, 0), "sf"),
    (datetime(2026, 7, 18, 7, 0), "third"),
    (datetime(2026, 7, 19, 7, 0), "final"),
]


def _round_for_date(dt: datetime) -> str:
    code = "group"
    for start, rc in _ROUND_DATES:
        if dt >= start:
            code = rc
    return code


def _event_datetime(event: dict) -> Optional[datetime]:
    ds = event.get("date")
    if not ds:
        return None
    try:
        return datetime.fromisoformat(ds.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


last_fetch: Optional[datetime] = None
last_error: Optional[str] = None


def _update_stage(db, team_id: int, round_code: str, winner: bool = False):
    from models import Team
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return
    new_stage = "winner" if winner else round_code
    if STAGE_REACHED.get(new_stage, 0) > STAGE_REACHED.get(team.stage_reached, 0):
        team.stage_reached = new_stage


def _recalc_bracket_points(db, league):
    from models import TournamentPick
    from bracket_utils import get_actual_bracket
    actual = get_actual_bracket(db)
    for pick in db.query(TournamentPick).filter(TournamentPick.league_id == league.id).all():
        pts = 0
        if actual["winner"] and pick.winner_id == actual["winner"]:
            pts += league.points_bracket_winner
        if actual["finalists"] and pick.finalist_1_id in actual["finalists"]:
            pts += league.points_bracket_finalist
        if actual["semis"]:
            if pick.semi_1_id in actual["semis"]:
                pts += league.points_bracket_semi
            if pick.semi_2_id in actual["semis"]:
                pts += league.points_bracket_semi
        pick.points_awarded = pts


def _dates_to_fetch(db) -> list[date]:
    """Return sorted list of dates that need an ESPN check."""
    from models import Match
    today = date.today()
    all_wc_dates = {WC_START + timedelta(days=i) for i in range((WC_END - WC_START).days + 1)}

    # Dates where we still have unfinished past matches (primary need)
    now = datetime.utcnow()
    scheduled_dates = {
        m.match_date.date()
        for m in db.query(Match).filter(Match.status != "finished", Match.match_date < now).all()
        if m.match_date
    }

    # Last 3 days (safety net for missed updates) + next 8 days
    # (so upcoming knockout matchups get pulled in as they're decided).
    window = {today + timedelta(days=i) for i in range(-3, 9)}

    return sorted((scheduled_dates | window) & all_wc_dates)


async def _fetch_espn(db: Session) -> int:
    """Fetch finished results from the ESPN API. Returns number of matches updated."""
    from models import Match, Team, Prediction, League, Goal
    from routers.predictions import calculate_points

    updated = 0

    # Safety: a finished match dated in the future is impossible — undo it. Guards against
    # stale provisional results ESPN may have served for not-yet-played knockout games.
    now = datetime.utcnow()
    for m in db.query(Match).filter(Match.status == "finished", Match.match_date > now).all():
        m.status = "scheduled"
        m.home_score = m.away_score = None
        m.home_score_reg = m.away_score_reg = None
        m.home_pens = m.away_pens = None
        if m.winner_team_id:
            for tid in (m.home_team_id, m.away_team_id):
                t = db.query(Team).filter(Team.id == tid).first()
                if t:
                    t.eliminated = False
            m.winner_team_id = None
        for pred in m.predictions:
            pred.points_awarded = None
        updated += 1
        logger.info(f"ESPN: reset future-dated finished match #{m.match_number}")
    if updated:
        db.commit()

    dates = _dates_to_fetch(db)
    if not dates:
        return updated
    async with httpx.AsyncClient(timeout=15.0) as client:
        for fetch_date in dates:
            try:
                resp = await client.get(ESPN_BASE, params={"dates": fetch_date.strftime("%Y%m%d")})
                resp.raise_for_status()
            except Exception as exc:
                logger.warning(f"ESPN fetch failed for {fetch_date}: {exc}")
                continue

            for event in resp.json().get("events", []):
                completed = bool(event.get("status", {}).get("type", {}).get("completed"))

                comp         = event["competitions"][0]
                competitors  = comp.get("competitors", [])
                home_comp    = next((c for c in competitors if c.get("homeAway") == "home"), None)
                away_comp    = next((c for c in competitors if c.get("homeAway") == "away"), None)
                if not home_comp or not away_comp:
                    continue

                home_abbr = ESPN_TO_CODE.get(home_comp["team"]["abbreviation"], home_comp["team"]["abbreviation"])
                away_abbr = ESPN_TO_CODE.get(away_comp["team"]["abbreviation"], away_comp["team"]["abbreviation"])

                home_team = db.query(Team).filter(Team.code == home_abbr).first()
                away_team = db.query(Team).filter(Team.code == away_abbr).first()
                if not home_team or not away_team:
                    # Placeholder side (e.g. "3RD", "RD32") — matchup not decided yet
                    continue

                # Determine the round from the match date (group vs r32/r16/qf/sf/third/final)
                ev_dt      = _event_datetime(event)
                round_code = _round_for_date(ev_dt) if ev_dt else "group"

                # Locate the DB match: prefer an exact team match; otherwise fill the next
                # empty knockout placeholder for this round (this is how the bracket fills in).
                match = db.query(Match).filter(
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                ).first()
                if not match and round_code != "group":
                    match = (
                        db.query(Match)
                        .filter(Match.round == round_code, Match.home_team_id.is_(None))
                        .order_by(Match.match_date, Match.id)
                        .first()
                    )
                    if match:
                        match.home_team_id = home_team.id
                        match.away_team_id = away_team.id
                        if ev_dt:
                            match.match_date = ev_dt
                        # Flush so the next "find empty placeholder" query sees this slot as
                        # filled (the session is autoflush=False, otherwise every matchup would
                        # overwrite the same first empty slot and only one would stick).
                        db.flush()
                        logger.info(f"ESPN: bracket — set {round_code} matchup {home_abbr} vs {away_abbr}")
                        if not completed:
                            updated += 1  # populated an upcoming matchup
                if not match:
                    logger.debug(f"ESPN: no DB slot for {home_abbr} vs {away_abbr} ({round_code})")
                    continue

                if not completed:
                    # ESPN says this game hasn't finished. If we have it wrongly marked finished
                    # (e.g. ESPN earlier served a provisional/simulated result for a future
                    # knockout match), undo it — ESPN is the source of truth.
                    if match.status == "finished":
                        match.status = "scheduled"
                        match.home_score = match.away_score = None
                        match.home_score_reg = match.away_score_reg = None
                        match.home_pens = match.away_pens = None
                        if match.winner_team_id:
                            for tid in (match.home_team_id, match.away_team_id):
                                t = db.query(Team).filter(Team.id == tid).first()
                                if t:
                                    t.eliminated = False
                            match.winner_team_id = None
                        for pred in match.predictions:
                            pred.points_awarded = None
                        updated += 1
                        logger.info(f"ESPN: reset wrongly-finished match {home_abbr} vs {away_abbr}")
                    continue  # matchup recorded; result not in yet

                try:
                    home_score_val = int(home_comp["score"])
                    away_score_val = int(away_comp["score"])
                except (KeyError, ValueError, TypeError):
                    continue

                already_finished = match.status == "finished"
                match.home_score = home_score_val
                match.away_score = away_score_val
                match.status     = "finished"
                # Regulation (90-min) score: group games never go to ET, so reg == final.
                # For knockouts we default reg to the final too, but only when not already
                # set — so an admin's manual 90-min correction for an extra-time game survives refetches.
                if match.round == "group":
                    match.home_score_reg = home_score_val
                    match.away_score_reg = away_score_val
                elif match.home_score_reg is None:
                    match.home_score_reg = home_score_val
                    match.away_score_reg = away_score_val

                # Knockout winner + stage/elimination tracking
                if match.round != "group":
                    winner_comp = next((c for c in competitors if c.get("winner")), None)
                    if winner_comp:
                        w_abbr = ESPN_TO_CODE.get(winner_comp["team"]["abbreviation"], winner_comp["team"]["abbreviation"])
                        match.winner_team_id = home_team.id if w_abbr == home_abbr else away_team.id
                    # Penalty shootout score, when ESPN provides it (don't clobber a manual entry)
                    try:
                        hp = home_comp.get("shootoutScore")
                        ap = away_comp.get("shootoutScore")
                        if hp is not None and ap is not None:
                            match.home_pens = int(hp)
                            match.away_pens = int(ap)
                    except (ValueError, TypeError):
                        pass
                    if match.winner_team_id:
                        loser_id = away_team.id if match.winner_team_id == home_team.id else home_team.id
                        _update_stage(db, match.winner_team_id, match.round, winner=(match.round == "final"))
                        loser = db.query(Team).filter(Team.id == loser_id).first()
                        if loser:
                            loser.eliminated = True

                # Goal scorers (only parse on first completion to avoid duplicates)
                if not already_finished:
                    db.query(Goal).filter(Goal.match_id == match.id).delete()
                    espn_id_to_team = {
                        home_comp["team"]["id"]: home_team,
                        away_comp["team"]["id"]: away_team,
                    }
                    for detail in comp.get("details", []):
                        if not detail.get("scoringPlay"):
                            continue
                        goal_team = espn_id_to_team.get(detail.get("team", {}).get("id"))
                        if not goal_team:
                            continue
                        minute_str = detail.get("clock", {}).get("displayValue", "")
                        try:
                            minute = int(minute_str.replace("'", "").split("+")[0])
                        except ValueError:
                            minute = None
                        athletes    = detail.get("athletesInvolved", [])
                        player_name = athletes[0]["displayName"] if athletes else "Unknown"
                        db.add(Goal(
                            match_id=match.id,
                            team_id=goal_team.id,
                            player_name=player_name,
                            minute=minute,
                            is_own_goal=detail.get("ownGoal", False),
                            is_penalty=detail.get("penaltyKick", False),
                        ))

                # Recalculate prediction points
                for pred in match.predictions:
                    league = db.query(League).filter(League.id == pred.league_id).first()
                    if league:
                        pred.points_awarded = calculate_points(pred, match, league)
                        if match.round in ("sf", "final"):
                            _recalc_bracket_points(db, league)

                updated += 1

    db.commit()
    return updated


async def _fetch_football_data(db: Session) -> int:
    """Fetch from football-data.org (requires API key). Returns matches updated."""
    from models import Match, Team, Prediction, League
    from routers.predictions import calculate_points

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            FOOTBALL_DATA_URL,
            headers={"X-Auth-Token": FOOTBALL_DATA_KEY},
            params={"status": "FINISHED"},
        )
        resp.raise_for_status()
        data = resp.json()

    updated = 0
    for m in data.get("matches", []):
        score = m.get("score", {})
        ft    = score.get("fullTime", {})
        home_score_val = ft.get("home")
        away_score_val = ft.get("away")
        if home_score_val is None:
            continue

        home_tla = (m.get("homeTeam", {}).get("tla") or "").upper()
        away_tla = (m.get("awayTeam", {}).get("tla") or "").upper()

        home_team = db.query(Team).filter(Team.code == home_tla).first()
        away_team = db.query(Team).filter(Team.code == away_tla).first()
        if not home_team or not away_team:
            continue

        match = db.query(Match).filter(
            Match.home_team_id == home_team.id,
            Match.away_team_id == away_team.id,
            Match.status != "finished",
        ).first()
        if not match:
            continue

        match.home_score = home_score_val
        match.away_score = away_score_val
        match.status     = "finished"

        winner_str = score.get("winner")
        if winner_str == "HOME_TEAM":
            match.winner_team_id = home_team.id
        elif winner_str == "AWAY_TEAM":
            match.winner_team_id = away_team.id

        for pred in match.predictions:
            league = db.query(League).filter(League.id == pred.league_id).first()
            if league:
                pred.points_awarded = calculate_points(pred, match, league)

        updated += 1

    db.commit()
    return updated


async def fetch_now(db: Session) -> dict:
    """Fetch results right now. Returns status dict."""
    global last_fetch, last_error
    result = {"espn": 0, "football_data": 0, "error": None}
    try:
        result["espn"] = await _fetch_espn(db)
    except Exception as e:
        result["error"] = str(e)
        last_error = str(e)
        logger.error(f"ESPN fetch failed: {e}")

    if FOOTBALL_DATA_KEY:
        try:
            result["football_data"] = await _fetch_football_data(db)
        except Exception as e:
            logger.warning(f"football-data.org fetch failed: {e}")

    last_fetch = datetime.utcnow()
    last_error = result["error"]
    return result


async def results_loop():
    """Background loop — runs forever, polls every POLL_INTERVAL seconds."""
    from database import SessionLocal
    logger.info(f"Results auto-fetch started (every {POLL_INTERVAL}s)")
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        db = SessionLocal()
        try:
            r = await fetch_now(db)
            if r["espn"] or r["football_data"]:
                logger.info(f"Auto-fetch: {r['espn']} updated via ESPN, {r['football_data']} via football-data.org")
        except Exception as e:
            logger.error(f"Results loop error: {e}")
        finally:
            db.close()
