from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import auth
from shared import templates

router = APIRouter()

POS_ORDER = {"GK": 0, "DF": 1, "MF": 2, "FW": 3}
POS_LABEL = {"GK": "Goalkeepers", "DF": "Defenders", "MF": "Midfielders", "FW": "Forwards"}


@router.get("/teams")
async def teams_list(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    all_teams = (
        db.query(models.Team)
        .order_by(models.Team.group_letter, models.Team.name)
        .all()
    )
    groups: dict[str, list] = {}
    for t in all_teams:
        groups.setdefault(t.group_letter, []).append(t)
    return templates.TemplateResponse(
        "teams/list.html",
        {"request": request, "user": user, "groups": groups},
    )


@router.get("/teams/{code}")
async def team_detail(code: str, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    team = db.query(models.Team).filter(models.Team.code == code.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    players = (
        db.query(models.Player)
        .filter(models.Player.team_id == team.id)
        .order_by(models.Player.squad_number)
        .all()
    )

    # Group by position in GK → DF → MF → FW order
    by_pos: dict[str, list] = {}
    for p in players:
        pos = p.position if p.position in POS_ORDER else "MF"
        by_pos.setdefault(pos, []).append(p)
    by_pos_ordered = {k: by_pos[k] for k in sorted(by_pos, key=lambda x: POS_ORDER.get(x, 99))}

    # Matches involving this team
    matches = (
        db.query(models.Match)
        .filter(
            (models.Match.home_team_id == team.id) | (models.Match.away_team_id == team.id)
        )
        .order_by(models.Match.match_date)
        .all()
    )

    return templates.TemplateResponse(
        "teams/detail.html",
        {
            "request": request,
            "user": user,
            "team": team,
            "by_pos": by_pos_ordered,
            "pos_label": POS_LABEL,
            "matches": matches,
            "player_count": len(players),
        },
    )
