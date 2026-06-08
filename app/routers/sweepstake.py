import random
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session

from database import get_db
import models
import auth
from shared import templates

router = APIRouter()


def _calc_sweep_points(league: models.League, db: Session) -> dict:
    """Returns {user_id: points} based on wins, draws, goals and clean sheets."""
    assignments = db.query(models.SweepstakeAssignment).filter_by(league_id=league.id).all()
    if not assignments:
        return {}

    team_ids = {a.team_id for a in assignments}
    pts_win         = (league.sweep_pts_win or 2)
    pts_draw        = (league.sweep_pts_draw or 0)
    pts_goal        = getattr(league, "sweep_pts_goal", 0) or 0
    pts_clean_sheet = getattr(league, "sweep_pts_clean_sheet", 0) or 0
    pts_goal_diff   = getattr(league, "sweep_pts_goal_diff", 0) or 0

    team_pts: dict[int, int] = {tid: 0 for tid in team_ids}

    finished = db.query(models.Match).filter(models.Match.status == "finished").all()
    for m in finished:
        h, a = m.home_score, m.away_score
        if h is None or a is None:
            continue

        # Win / draw points
        if m.round == "group":
            if h > a:
                if m.home_team_id in team_pts:
                    team_pts[m.home_team_id] += pts_win
            elif a > h:
                if m.away_team_id in team_pts:
                    team_pts[m.away_team_id] += pts_win
            else:
                if m.home_team_id in team_pts:
                    team_pts[m.home_team_id] += pts_draw
                if m.away_team_id in team_pts:
                    team_pts[m.away_team_id] += pts_draw
        else:
            if m.winner_team_id and m.winner_team_id in team_pts:
                team_pts[m.winner_team_id] += pts_win

        # Goal points (goals scored by each side)
        if pts_goal:
            if m.home_team_id in team_pts:
                team_pts[m.home_team_id] += h * pts_goal
            if m.away_team_id in team_pts:
                team_pts[m.away_team_id] += a * pts_goal

        # Clean sheet points (0 goals conceded in 90 min)
        if pts_clean_sheet:
            if a == 0 and m.home_team_id in team_pts:
                team_pts[m.home_team_id] += pts_clean_sheet
            if h == 0 and m.away_team_id in team_pts:
                team_pts[m.away_team_id] += pts_clean_sheet

        # Goal difference points (positive margin only)
        if pts_goal_diff:
            if m.home_team_id in team_pts:
                team_pts[m.home_team_id] += max(0, h - a) * pts_goal_diff
            if m.away_team_id in team_pts:
                team_pts[m.away_team_id] += max(0, a - h) * pts_goal_diff

    user_pts: dict[int, int] = {}
    for a in assignments:
        user_pts[a.user_id] = user_pts.get(a.user_id, 0) + team_pts.get(a.team_id, 0)

    return user_pts


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

    user_assignments: dict = {}
    for a in assignments:
        user_assignments.setdefault(a.user_id, []).append(a.team)

    # Sweepstake leaderboard (only meaningful after draw)
    sweep_pts = _calc_sweep_points(league, db) if league.sweepstake_drawn else {}
    sweep_lb = sorted(
        [{"user": m.user, "pts": sweep_pts.get(m.user_id, 0), "teams": user_assignments.get(m.user_id, [])}
         for m in members],
        key=lambda x: x["pts"], reverse=True,
    )

    groups = league.sweepstake_groups

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
            "sweep_lb": sweep_lb,
            "groups": groups,
        },
    )


@router.post("/leagues/{league_id}/sweepstake/pay/{member_user_id}")
async def toggle_paid(request: Request, league_id: int, member_user_id: int, db: Session = Depends(get_db)):
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

    db.query(models.SweepstakeAssignment).filter_by(league_id=league_id).delete()

    groups = league.sweepstake_groups
    if groups:
        # Group draw: each paid member gets 1 random team per group
        for group in groups:
            team_ids = [gt.team_id for gt in group.teams]
            random.shuffle(team_ids)
            for i, member in enumerate(paid_members):
                if i < len(team_ids):
                    db.add(models.SweepstakeAssignment(
                        league_id=league_id,
                        user_id=member.user_id,
                        team_id=team_ids[i],
                        group_id=group.id,
                    ))
    else:
        # Classic random draw
        all_teams = db.query(models.Team).all()
        slots = len(paid_members) * league.sweepstake_teams_per_person
        pool = (all_teams * (slots // len(all_teams) + 1))[:slots]
        random.shuffle(pool)
        idx = 0
        for m in paid_members:
            for _ in range(league.sweepstake_teams_per_person):
                db.add(models.SweepstakeAssignment(
                    league_id=league_id,
                    user_id=m.user_id,
                    team_id=pool[idx].id,
                ))
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
    db.query(models.SweepstakeAssignment).filter_by(league_id=league_id).delete()
    league.sweepstake_drawn = False
    db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)


# ── Group management ─────────────────────────────────────────

@router.get("/leagues/{league_id}/sweepstake/groups")
async def groups_page(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
    all_teams = db.query(models.Team).order_by(models.Team.group_letter, models.Team.name).all()
    # Teams already assigned to any group in this league
    assigned_team_ids = {
        gt.team_id
        for g in league.sweepstake_groups
        for gt in g.teams
    }
    return templates.TemplateResponse("sweepstake/groups.html", {
        "request": request,
        "user": user,
        "league": league,
        "groups": league.sweepstake_groups,
        "all_teams": all_teams,
        "assigned_team_ids": assigned_team_ids,
    })


@router.post("/leagues/{league_id}/sweepstake/groups/create")
async def create_group(request: Request, league_id: int, name: str = Form(...), db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
    order = len(league.sweepstake_groups)
    db.add(models.SweepstakeGroup(league_id=league_id, name=name.strip()[:50], order_index=order))
    db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake/groups", status_code=303)


@router.post("/leagues/{league_id}/sweepstake/groups/{group_id}/delete")
async def delete_group(request: Request, league_id: int, group_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
    grp = db.query(models.SweepstakeGroup).filter_by(id=group_id, league_id=league_id).first()
    if grp:
        db.delete(grp)
        db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake/groups", status_code=303)


@router.post("/leagues/{league_id}/sweepstake/groups/{group_id}/teams/add")
async def add_team_to_group(request: Request, league_id: int, group_id: int, team_id: int = Form(...), db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
    grp = db.query(models.SweepstakeGroup).filter_by(id=group_id, league_id=league_id).first()
    if grp:
        existing = db.query(models.SweepstakeGroupTeam).filter_by(group_id=group_id, team_id=team_id).first()
        if not existing:
            db.add(models.SweepstakeGroupTeam(group_id=group_id, team_id=team_id))
            db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake/groups", status_code=303)


@router.post("/leagues/{league_id}/sweepstake/groups/{group_id}/teams/{team_id}/remove")
async def remove_team_from_group(request: Request, league_id: int, group_id: int, team_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
    gt = db.query(models.SweepstakeGroupTeam).filter_by(group_id=group_id, team_id=team_id).first()
    if gt:
        db.delete(gt)
        db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake/groups", status_code=303)
