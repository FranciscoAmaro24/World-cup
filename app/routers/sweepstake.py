import random
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session
import os

from database import get_db
import models
import auth
from shared import templates

router = APIRouter()


@router.get("/leagues/{league_id}/sweepstake")
async def sweepstake_page(request: Request, league_id: int, db: Session = Depends(get_db)):
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

    members = league.members
    assignments = league.sweepstake_assignments
    paid_count = sum(1 for m in members if m.sweepstake_paid)
    pot = paid_count * league.sweepstake_buy_in

    user_teams = [a for a in assignments if a.user_id == user.id]

    user_assignments = {}
    for a in assignments:
        user_assignments.setdefault(a.user_id, []).append(a.team)

    return templates.TemplateResponse(
        "sweepstake/detail.html",
        {
            "request": request,
            "user": user,
            "league": league,
            "members": members,
            "pot": pot,
            "paid_count": paid_count,
            "user_teams": user_teams,
            "user_assignments": user_assignments,
            "is_admin": league.admin_id == user.id,
            "error": None,
        },
    )


@router.post("/leagues/{league_id}/sweepstake/pay/{member_user_id}")
async def toggle_paid(
    request: Request,
    league_id: int,
    member_user_id: int,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
    member = db.query(models.LeagueMember).filter(
        models.LeagueMember.league_id == league_id,
        models.LeagueMember.user_id == member_user_id,
    ).first()
    if member:
        member.sweepstake_paid = not member.sweepstake_paid
        db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)


@router.post("/leagues/{league_id}/sweepstake/draw")
async def draw_teams(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id or league.sweepstake_drawn:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)

    paid_members = [m for m in league.members if m.sweepstake_paid]
    if not paid_members:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)

    all_teams = db.query(models.Team).all()
    slots_needed = len(paid_members) * league.sweepstake_teams_per_person
    pool = all_teams * (slots_needed // len(all_teams) + 1)
    pool = pool[:slots_needed]
    random.shuffle(pool)

    db.query(models.SweepstakeAssignment).filter(
        models.SweepstakeAssignment.league_id == league_id
    ).delete()

    idx = 0
    for m in paid_members:
        for _ in range(league.sweepstake_teams_per_person):
            assignment = models.SweepstakeAssignment(
                league_id=league_id,
                user_id=m.user_id,
                team_id=pool[idx].id,
            )
            db.add(assignment)
            idx += 1

    league.sweepstake_drawn = True
    db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)


@router.post("/leagues/{league_id}/sweepstake/reset")
async def reset_draw(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
    db.query(models.SweepstakeAssignment).filter(
        models.SweepstakeAssignment.league_id == league_id
    ).delete()
    league.sweepstake_drawn = False
    db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
