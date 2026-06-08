"""
Pre-tournament bracket picks.
Users predict: tournament winner, finalist (runner-up), and 2 losing semi-finalists.
Locked once the first knockout match kicks off.
"""
from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session
import os

from database import get_db
import models
import auth
from shared import templates
from bracket_utils import get_actual_bracket, calc_bracket_points, is_bracket_locked, bracket_lock_status

router = APIRouter()


@router.get("/leagues/{league_id}/bracket")
async def bracket_page(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league:
        return RedirectResponse("/leagues", status_code=303)
    membership = db.query(models.LeagueMember).filter(
        models.LeagueMember.league_id == league_id,
        models.LeagueMember.user_id == user.id,
    ).first()
    if not membership:
        return RedirectResponse("/leagues", status_code=303)

    teams = db.query(models.Team).order_by(models.Team.group_letter, models.Team.name).all()
    lock_status = bracket_lock_status(db)
    locked = lock_status != "open"
    pick = db.query(models.TournamentPick).filter(
        models.TournamentPick.user_id == user.id,
        models.TournamentPick.league_id == league_id,
    ).first()

    # Leaderboard of bracket picks
    all_picks = db.query(models.TournamentPick).filter(
        models.TournamentPick.league_id == league_id
    ).all()
    actual = get_actual_bracket(db)
    pick_rows = []
    for p in all_picks:
        any_result = actual["winner"] or actual["finalists"] or actual["semis"] or actual["quarters"]
        pts = calc_bracket_points(p, league, actual) if any_result else p.points_awarded
        pick_rows.append({"user": p.user, "pick": p, "points": pts})
    pick_rows.sort(key=lambda x: x["points"], reverse=True)

    return templates.TemplateResponse(
        "bracket/picks.html",
        {
            "request": request,
            "user": user,
            "league": league,
            "teams": teams,
            "locked": locked,
            "lock_status": lock_status,
            "pick": pick,
            "pick_rows": pick_rows,
            "actual": actual,
        },
    )


@router.post("/leagues/{league_id}/bracket")
async def save_bracket(
    request: Request,
    league_id: int,
    quarter_1_id: int = Form(0),
    quarter_2_id: int = Form(0),
    quarter_3_id: int = Form(0),
    quarter_4_id: int = Form(0),
    semi_1_id: int = Form(0),
    semi_2_id: int = Form(0),
    finalist_1_id: int = Form(0),
    winner_id: int = Form(0),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league:
        return RedirectResponse("/leagues", status_code=303)
    membership = db.query(models.LeagueMember).filter(
        models.LeagueMember.league_id == league_id,
        models.LeagueMember.user_id == user.id,
    ).first()
    if not membership or is_bracket_locked(db):
        return RedirectResponse(f"/leagues/{league_id}/bracket", status_code=303)

    def valid(tid):
        return tid if tid and tid > 0 else None

    pick = db.query(models.TournamentPick).filter(
        models.TournamentPick.user_id == user.id,
        models.TournamentPick.league_id == league_id,
    ).first()
    fields = dict(
        quarter_1_id=valid(quarter_1_id),
        quarter_2_id=valid(quarter_2_id),
        quarter_3_id=valid(quarter_3_id),
        quarter_4_id=valid(quarter_4_id),
        semi_1_id=valid(semi_1_id),
        semi_2_id=valid(semi_2_id),
        finalist_1_id=valid(finalist_1_id),
        winner_id=valid(winner_id),
    )
    if pick:
        for k, v in fields.items():
            setattr(pick, k, v)
        pick.submitted_at = datetime.utcnow()
    else:
        pick = models.TournamentPick(user_id=user.id, league_id=league_id, **fields)
        db.add(pick)
    db.commit()
    return RedirectResponse(f"/leagues/{league_id}/bracket", status_code=303)
