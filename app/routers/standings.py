"""Group stage standings tables computed live from match results."""
from fastapi import APIRouter, Request, Depends

from sqlalchemy.orm import Session
import os

from database import get_db
import models
import auth
from shared import templates

router = APIRouter()

GROUPS = list("ABCDEFGHIJKL")


def compute_group(db: Session, letter: str) -> list[dict]:
    teams = db.query(models.Team).filter(models.Team.group_letter == letter).all()
    stats = {
        t.id: {"team": t, "P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "GD": 0, "Pts": 0}
        for t in teams
    }
    matches = (
        db.query(models.Match)
        .filter(models.Match.group_letter == letter, models.Match.status == "finished")
        .all()
    )
    for m in matches:
        if m.home_score is None or m.home_team_id not in stats or m.away_team_id not in stats:
            continue
        h, a, hg, ag = m.home_team_id, m.away_team_id, m.home_score, m.away_score
        for tid in (h, a):
            stats[tid]["P"] += 1
        stats[h]["GF"] += hg; stats[h]["GA"] += ag; stats[h]["GD"] += hg - ag
        stats[a]["GF"] += ag; stats[a]["GA"] += hg; stats[a]["GD"] += ag - hg
        if hg > ag:
            stats[h]["W"] += 1; stats[h]["Pts"] += 3; stats[a]["L"] += 1
        elif ag > hg:
            stats[a]["W"] += 1; stats[a]["Pts"] += 3; stats[h]["L"] += 1
        else:
            stats[h]["D"] += 1; stats[h]["Pts"] += 1; stats[a]["D"] += 1; stats[a]["Pts"] += 1
    return sorted(stats.values(), key=lambda x: (-x["Pts"], -x["GD"], -x["GF"]))


def _result(h, a):
    return "H" if h > a else ("A" if a > h else "D")


@router.get("/leaderboard")
async def global_leaderboard(request: Request, db: Session = Depends(get_db)):
    """Site-wide leaderboard ranking every user across all their predictions.

    Predictions are unified across leagues, so each (user, match) is deduped to the
    latest-submitted prediction and scored once with the global per-round point scheme.
    """
    from routers.predictions import calculate_points
    user = auth.get_current_user(request, db)
    global_league = db.query(models.League).filter(models.League.category == "global").first()

    finished = {
        m.id: m for m in db.query(models.Match).filter(models.Match.status == "finished").all()
        if m.home_score is not None and m.away_score is not None
    }

    # Canonical prediction per (user, match): latest submitted wins (scores are identical
    # across a user's leagues).
    by_user: dict[int, dict[int, models.Prediction]] = {}
    for p in db.query(models.Prediction).all():
        d = by_user.setdefault(p.user_id, {})
        cur = d.get(p.match_id)
        if cur is None or (p.submitted_at and (not cur.submitted_at or p.submitted_at > cur.submitted_at)):
            d[p.match_id] = p

    bracket_by_user: dict[int, int] = {}
    if global_league:
        for tp in db.query(models.TournamentPick).filter(
            models.TournamentPick.league_id == global_league.id
        ).all():
            bracket_by_user[tp.user_id] = tp.points_awarded or 0

    rows = []
    for u in db.query(models.User).all():
        canon = by_user.get(u.id, {})
        if not canon and u.id not in bracket_by_user:
            continue  # never predicted anything — skip
        match_pts = sum(
            calculate_points(p, finished[mid]) for mid, p in canon.items() if mid in finished
        )
        bracket_pts = bracket_by_user.get(u.id, 0)
        rows.append({
            "user": u,
            "match_pts": match_pts,
            "bracket_pts": bracket_pts,
            "total": match_pts + bracket_pts,
            "predictions": len(canon),
        })

    rows.sort(key=lambda x: (-x["total"], -x["predictions"]))
    for i, row in enumerate(rows):
        row["rank"] = i + 1
    return templates.TemplateResponse(
        "leaderboard.html", {"request": request, "user": user, "rows": rows}
    )


@router.get("/standings")
async def standings(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    groups_data = {}
    for letter in GROUPS:
        rows = compute_group(db, letter)
        if rows:
            groups_data[letter] = rows
    return templates.TemplateResponse(
        "standings.html",
        {"request": request, "user": user, "groups_data": groups_data},
    )
