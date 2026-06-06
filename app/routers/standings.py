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
