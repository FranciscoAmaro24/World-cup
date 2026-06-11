import random
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session

from database import get_db
import models
import auth
from shared import templates

router = APIRouter()

# FIFA-based default draw pots for WC 2026
_FIFA_POTS: dict[int, list[str]] = {
    1: ["ARG", "FRA", "ESP", "ENG", "BRA", "POR", "NED", "GER", "MAR"],
    2: ["AUT", "SUI", "JPN", "SEN", "KOR", "CRO", "SWE", "MEX", "TUR", "NOR", "COL", "URU", "BEL"],
    3: ["ECU", "CIV", "ALG", "AUS", "TUN", "GHA", "CZE", "KSA", "UZB", "COD", "RSA", "IRN", "USA"],
    4: ["IRQ", "EGY", "PAR", "SCO", "PAN", "JOR", "NZL", "CAN", "QAT", "BIH", "CUW", "HAI", "CPV"],
}
_POT_NAMES = {1: "Pot 1: Favourites", 2: "Pot 2: Contenders", 3: "Pot 3: Dark Horses", 4: "Pot 4: Underdogs"}


def _calc_sweep_points(league: models.League, db: Session) -> dict:
    """Returns {user_id: points} based on wins, draws, goals, clean sheets and big win bonus."""
    assignments = db.query(models.SweepstakeAssignment).filter_by(league_id=league.id).all()
    if not assignments:
        return {}

    team_ids = {a.team_id for a in assignments}
    default_pts_win     = (league.sweep_pts_win or 2)
    pts_draw            = (league.sweep_pts_draw or 0)
    pts_goal            = getattr(league, "sweep_pts_goal", 0) or 0
    pts_clean_sheet     = getattr(league, "sweep_pts_clean_sheet", 0) or 0
    big_win_threshold   = getattr(league, "sweep_big_win_threshold", 0) or 0
    big_win_pts         = getattr(league, "sweep_big_win_pts", 0) or 0

    upset_pts = getattr(league, "sweep_upset_pts", 0) or 0

    # Per-group maps (keyed by team_id)
    group_pts_win_map: dict[int, int] = {}   # team_id -> pts_win override
    team_tier: dict[int, int] = {}           # team_id -> group.order_index (lower = better)
    for grp in league.sweepstake_groups:
        for gt in grp.teams:
            team_tier[gt.team_id] = grp.order_index
        if grp.pts_win is not None:
            for gt in grp.teams:
                group_pts_win_map[gt.team_id] = grp.pts_win

    def win_pts(team_id: int) -> int:
        return group_pts_win_map.get(team_id, default_pts_win)

    def is_upset(winner_id: int, loser_id: int) -> bool:
        """True when winner is from a higher order_index (worse) group than the loser."""
        if not upset_pts:
            return False
        wt = team_tier.get(winner_id)
        lt = team_tier.get(loser_id)
        return wt is not None and lt is not None and wt > lt

    team_pts: dict[int, int] = {tid: 0 for tid in team_ids}

    finished = db.query(models.Match).filter(models.Match.status == "finished").all()
    for m in finished:
        h, a = m.home_score, m.away_score
        if h is None or a is None:
            continue

        # Win / draw points (per-group override + upset bonus supported)
        if m.round == "group":
            if h > a:
                if m.home_team_id in team_pts:
                    team_pts[m.home_team_id] += win_pts(m.home_team_id)
                    if is_upset(m.home_team_id, m.away_team_id):
                        team_pts[m.home_team_id] += upset_pts
            elif a > h:
                if m.away_team_id in team_pts:
                    team_pts[m.away_team_id] += win_pts(m.away_team_id)
                    if is_upset(m.away_team_id, m.home_team_id):
                        team_pts[m.away_team_id] += upset_pts
            else:
                if m.home_team_id in team_pts:
                    team_pts[m.home_team_id] += pts_draw
                if m.away_team_id in team_pts:
                    team_pts[m.away_team_id] += pts_draw
        else:
            if m.winner_team_id and m.winner_team_id in team_pts:
                loser_id = m.away_team_id if m.winner_team_id == m.home_team_id else m.home_team_id
                team_pts[m.winner_team_id] += win_pts(m.winner_team_id)
                if is_upset(m.winner_team_id, loser_id):
                    team_pts[m.winner_team_id] += upset_pts

        # Goal points (goals scored in 90 min)
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

        # Big win bonus (when GD >= threshold in 90 min)
        if big_win_pts and big_win_threshold:
            if (h - a) >= big_win_threshold and m.home_team_id in team_pts:
                team_pts[m.home_team_id] += big_win_pts
            if (a - h) >= big_win_threshold and m.away_team_id in team_pts:
                team_pts[m.away_team_id] += big_win_pts

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
            "is_admin": league.admin_id == user.id or user.is_superadmin,
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
    if not league or league.admin_id != user.id and not user.is_superadmin:
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
    if not league or league.admin_id != user.id and not user.is_superadmin or league.sweepstake_drawn:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)

    paid_members = [m for m in league.members if m.sweepstake_paid]
    if not paid_members:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)

    db.query(models.SweepstakeAssignment).filter_by(league_id=league_id).delete()

    groups = league.sweepstake_groups
    if groups:
        # Group draw: each paid member gets 1 random team per group.
        # Member order is shuffled independently per group so a good draw
        # in one pot doesn't correlate with a good draw in another.
        for group in groups:
            team_ids = [gt.team_id for gt in group.teams]
            random.shuffle(team_ids)
            member_order = list(paid_members)
            random.shuffle(member_order)
            for i, member in enumerate(member_order):
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
    return RedirectResponse(f"/leagues/{league_id}/sweepstake/reveal", status_code=303)


@router.post("/leagues/{league_id}/sweepstake/reset")
async def reset_draw(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id and not user.is_superadmin:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
    db.query(models.SweepstakeAssignment).filter_by(league_id=league_id).delete()
    league.sweepstake_drawn = False
    db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)


@router.get("/leagues/{league_id}/sweepstake/reveal")
async def reveal_page(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league:
        return RedirectResponse("/leagues", status_code=303)
    membership = db.query(models.LeagueMember).filter_by(
        league_id=league_id, user_id=user.id
    ).first()
    if not membership and not user.is_superadmin:
        return RedirectResponse("/leagues", status_code=303)
    if not league.sweepstake_drawn:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)

    assignments = (
        db.query(models.SweepstakeAssignment)
        .filter_by(league_id=league_id)
        .all()
    )

    by_user: dict = {}
    for a in assignments:
        by_user.setdefault(a.user_id, []).append(a)
    for lst in by_user.values():
        lst.sort(key=lambda a: (a.group.order_index if a.group else 99))

    draw_results = [
        {"user": lst[0].user, "assignments": lst}
        for lst in by_user.values() if lst
    ]
    random.shuffle(draw_results)

    all_teams = db.query(models.Team).all()

    return templates.TemplateResponse(
        "sweepstake/reveal.html",
        {
            "request": request,
            "user": user,
            "league": league,
            "draw_results": draw_results,
            "all_teams": all_teams,
        },
    )


# ── Group management ─────────────────────────────────────────

@router.get("/leagues/{league_id}/sweepstake/groups")
async def groups_page(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id and not user.is_superadmin:
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
    if not league or league.admin_id != user.id and not user.is_superadmin:
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
    if not league or league.admin_id != user.id and not user.is_superadmin:
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
    if not league or league.admin_id != user.id and not user.is_superadmin:
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
    if not league or league.admin_id != user.id and not user.is_superadmin:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
    gt = db.query(models.SweepstakeGroupTeam).filter_by(group_id=group_id, team_id=team_id).first()
    if gt:
        db.delete(gt)
        db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake/groups", status_code=303)


@router.post("/leagues/{league_id}/sweepstake/groups/{group_id}/update")
async def update_group_settings(
    request: Request, league_id: int, group_id: int,
    pts_win: str = Form(""), db: Session = Depends(get_db)
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id and not user.is_superadmin:
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)
    grp = db.query(models.SweepstakeGroup).filter_by(id=group_id, league_id=league_id).first()
    if grp:
        grp.pts_win = int(pts_win) if pts_win.strip().isdigit() else None
        db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake/groups", status_code=303)


@router.post("/leagues/{league_id}/sweepstake/groups/setup-default")
async def setup_default_groups(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or (league.admin_id != user.id and not user.is_superadmin):
        return RedirectResponse(f"/leagues/{league_id}/sweepstake", status_code=303)

    # Clear existing groups and their team assignments
    for grp in list(league.sweepstake_groups):
        db.delete(grp)
    db.flush()

    # Build code → team map from DB
    teams = {t.code: t for t in db.query(models.Team).all()}

    for pot_num in range(1, 5):
        grp = models.SweepstakeGroup(
            league_id=league_id,
            name=_POT_NAMES[pot_num],
            order_index=pot_num - 1,
        )
        db.add(grp)
        db.flush()
        for code in _FIFA_POTS[pot_num]:
            team = teams.get(code)
            if team:
                db.add(models.SweepstakeGroupTeam(group_id=grp.id, team_id=team.id))

    db.commit()
    return RedirectResponse(f"/leagues/{league_id}/sweepstake/groups", status_code=303)
