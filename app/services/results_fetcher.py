"""
Auto-results fetcher.

Primary source  : openfootball/worldcup.json on GitHub (no API key needed)
Secondary source: football-data.org  (set FOOTBALL_DATA_API_KEY env var)

Runs as an asyncio background task every POLL_INTERVAL seconds.
Also exposes `fetch_now(db)` for the manual admin trigger.
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("RESULTS_POLL_SECONDS", "300"))  # 5 min default

OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
)
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_URL = "https://api.football-data.org/v4/competitions/WC/matches"

ROUND_MAP = {
    "group a": ("group", "A"), "group b": ("group", "B"),
    "group c": ("group", "C"), "group d": ("group", "D"),
    "group e": ("group", "E"), "group f": ("group", "F"),
    "group g": ("group", "G"), "group h": ("group", "H"),
    "group i": ("group", "I"), "group j": ("group", "J"),
    "group k": ("group", "K"), "group l": ("group", "L"),
    "round of 32": ("r32", None), "last 32": ("r32", None),
    "round of 16": ("r16", None), "last 16": ("r16", None),
    "quarter": ("qf", None),
    "semi": ("sf", None),
    "third": ("third", None), "3rd": ("third", None),
    "final": ("final", None),
}

STAGE_REACHED = {
    "group": 0, "r32": 1, "r16": 2, "qf": 3, "sf": 4, "final": 5, "winner": 6,
}

last_fetch: Optional[datetime] = None
last_error: Optional[str] = None


def _parse_round(name: str):
    n = name.lower()
    for key, val in ROUND_MAP.items():
        if key in n:
            return val
    return ("group", None)


def _winner_from_score(score: dict, home_id: int, away_id: int) -> Optional[int]:
    """Determine advancing team from openfootball score object."""
    if "p" in score:
        p = score["p"]
        return home_id if p[0] > p[1] else away_id
    if "et" in score:
        et = score["et"]
        if et[0] != et[1]:
            return home_id if et[0] > et[1] else away_id
    ft = score.get("ft", [])
    if len(ft) == 2 and ft[0] != ft[1]:
        return home_id if ft[0] > ft[1] else away_id
    return None


def _next_match_number(db) -> int:
    from models import Match
    max_num = db.query(Match.match_number).order_by(Match.match_number.desc()).first()
    return (max_num[0] + 1) if max_num else 100


def _update_stage(db, team_id: int, round_code: str, winner: bool = False):
    from models import Team
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        return
    new_stage = "winner" if winner else round_code
    if STAGE_REACHED.get(new_stage, 0) > STAGE_REACHED.get(team.stage_reached, 0):
        team.stage_reached = new_stage


def _recalc_bracket_points(db, league):
    """Recompute bracket pick points for all members of a league."""
    from models import TournamentPick, Match, Team
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


async def _fetch_openfootball(db: Session) -> int:
    """Fetch from openfootball GitHub. Returns number of matches updated."""
    from models import Match, Team, Prediction, League
    from routers.predictions import calculate_points

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(OPENFOOTBALL_URL)
        resp.raise_for_status()
        data = resp.json()

    updated = 0
    for rnd in data.get("rounds", []):
        round_name = rnd.get("name", "")
        round_code, group_letter = _parse_round(round_name)

        for m in rnd.get("matches", []):
            score = m.get("score")
            ft = score.get("ft") if score else None
            if not ft or len(ft) < 2:
                continue  # not played yet
            home_score_val, away_score_val = ft[0], ft[1]

            t1 = m.get("team1", {})
            t2 = m.get("team2", {})
            home_code = (t1.get("code") or "").upper()
            away_code = (t2.get("code") or "").upper()
            if not home_code or not away_code:
                continue

            home_team = db.query(Team).filter(Team.code == home_code).first()
            away_team = db.query(Team).filter(Team.code == away_code).first()
            if not home_team or not away_team:
                continue

            # Try to find the match in our DB
            match = db.query(Match).filter(
                Match.home_team_id == home_team.id,
                Match.away_team_id == away_team.id,
            ).first()

            if not match:
                # Knockout match not yet in DB — create it
                if round_code == "group":
                    continue  # group matches should already exist
                date_str = m.get("date", "2026-07-01")
                time_str = m.get("time", "19:00")
                try:
                    match_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                except ValueError:
                    match_dt = datetime(2026, 7, 1, 19, 0)
                venue = m.get("ground", {})
                venue_str = venue.get("name", "TBD") if isinstance(venue, dict) else str(venue)
                match = Match(
                    match_number=_next_match_number(db),
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    group_letter=group_letter,
                    round=round_code,
                    match_date=match_dt,
                    venue=venue_str,
                )
                db.add(match)
                db.flush()
                logger.info(f"Created new {round_code} match: {home_code} vs {away_code}")

            already_finished = match.status == "finished"

            match.home_score = home_score_val
            match.away_score = away_score_val
            match.status = "finished"

            # Parse goal scorers (only if not already loaded)
            if not already_finished:
                from models import Goal
                db.query(Goal).filter(Goal.match_id == match.id).delete()
                for g in m.get("goals", []):
                    team_side = g.get("team", 0)  # 1=home, 2=away
                    team_id = home_team.id if team_side == 1 else away_team.id
                    og = str(g.get("type", "")).lower() == "og"
                    pen = str(g.get("type", "")).lower() == "pen"
                    name = g.get("name", "Unknown")
                    minute = g.get("minute")
                    if isinstance(minute, str):
                        minute = int(minute.replace("+", "").split("+")[0]) if minute else None
                    db.add(Goal(
                        match_id=match.id,
                        team_id=team_id,
                        player_name=name,
                        minute=minute,
                        is_own_goal=og,
                        is_penalty=pen,
                    ))

            # Determine advancing team for knockout
            if round_code != "group" and score:
                winner_id = _winner_from_score(score, home_team.id, away_team.id)
                match.winner_team_id = winner_id
                if winner_id:
                    loser_id = away_team.id if winner_id == home_team.id else home_team.id
                    _update_stage(db, winner_id, round_code, winner=(round_code == "final"))
                    loser_team = db.query(Team).filter(Team.id == loser_id).first()
                    if loser_team:
                        loser_team.eliminated = True

            # Calculate points for every prediction across all leagues
            for pred in match.predictions:
                league = db.query(League).filter(League.id == pred.league_id).first()
                if league:
                    pred.points_awarded = calculate_points(pred, match, league)
                    if round_code in ("sf", "final"):
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
        ft = score.get("fullTime", {})
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
        match.status = "finished"

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
    result = {"openfootball": 0, "football_data": 0, "error": None}
    try:
        result["openfootball"] = await _fetch_openfootball(db)
    except Exception as e:
        result["error"] = str(e)
        last_error = str(e)
        logger.error(f"openfootball fetch failed: {e}")

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
            if r["openfootball"] or r["football_data"]:
                logger.info(f"Auto-fetch: {r['openfootball']} updated via openfootball, {r['football_data']} via football-data.org")
        except Exception as e:
            logger.error(f"Results loop error: {e}")
        finally:
            db.close()
