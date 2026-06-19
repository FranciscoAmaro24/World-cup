import random
import string
import uuid
import os
from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
import models
import auth
from shared import templates
from image_utils import process_image


def _member_counts(db: Session, league_ids: list[int]) -> dict[int, int]:
    """Single GROUP BY query returning {league_id: member_count} for all given league ids."""
    if not league_ids:
        return {}
    rows = (
        db.query(models.LeagueMember.league_id, func.count(models.LeagueMember.id))
        .filter(models.LeagueMember.league_id.in_(league_ids))
        .group_by(models.LeagueMember.league_id)
        .all()
    )
    return {lid: cnt for lid, cnt in rows}

_uploads_base = os.getenv("UPLOADS_DIR", os.path.join(os.path.dirname(__file__), "..", "static", "uploads"))
LEAGUE_UPLOAD_DIR = os.path.join(_uploads_base, "leagues")
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE = 10 * 1024 * 1024

router = APIRouter(prefix="/leagues")


def _gen_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _get_leaderboard(league: models.League, db: Session):
    # Two bulk queries instead of 2×N per-member queries
    all_preds = db.query(models.Prediction).filter(
        models.Prediction.league_id == league.id,
        models.Prediction.points_awarded.isnot(None),
    ).all()
    all_picks = db.query(models.TournamentPick).filter(
        models.TournamentPick.league_id == league.id,
    ).all()

    pred_pts: dict[int, int] = {}
    pred_count: dict[int, int] = {}
    for p in all_preds:
        pred_pts[p.user_id] = pred_pts.get(p.user_id, 0) + p.points_awarded
        pred_count[p.user_id] = pred_count.get(p.user_id, 0) + 1

    pick_by_user = {p.user_id: p for p in all_picks}

    rows = []
    for m in league.members:
        match_pts   = pred_pts.get(m.user_id, 0)
        bracket_pick = pick_by_user.get(m.user_id)
        bracket_pts  = bracket_pick.points_awarded if bracket_pick else 0
        bonus_pts    = m.bonus_points or 0
        rows.append({
            "user":           m.user,
            "member":         m,
            "points":         match_pts + bracket_pts + bonus_pts,
            "match_points":   match_pts,
            "bracket_points": bracket_pts,
            "bonus_points":   bonus_pts,
            "predictions":    pred_count.get(m.user_id, 0),
            "has_bracket":    bracket_pick is not None,
        })
    rows.sort(key=lambda x: x["points"], reverse=True)
    for i, row in enumerate(rows):
        row["rank"] = i + 1
    return rows


@router.get("")
async def leagues_list(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    memberships = db.query(models.LeagueMember).filter(models.LeagueMember.user_id == user.id).all()
    fav_ids = {m.league_id for m in memberships if m.is_favourite}
    member_leagues = [m.league for m in memberships]
    member_ids = {l.id for l in member_leagues}

    # Superadmins also see leagues they own but aren't a member of
    admin_only_leagues = []
    if user.is_superadmin:
        owned = db.query(models.League).filter(models.League.admin_id == user.id).all()
        admin_only_leagues = [l for l in owned if l.id not in member_ids]

    all_leagues = member_leagues + admin_only_leagues
    fav_leagues = [l for l in member_leagues if l.id in fav_ids]
    other_leagues = [l for l in member_leagues if l.id not in fav_ids]
    all_shown = all_leagues + admin_only_leagues
    counts = _member_counts(db, [l.id for l in all_shown])
    return templates.TemplateResponse(
        "leagues/list.html", {
            "request": request, "user": user,
            "leagues": all_leagues,
            "fav_leagues": fav_leagues,
            "other_leagues": other_leagues,
            "fav_ids": fav_ids,
            "admin_only_leagues": admin_only_leagues,
            "member_counts": counts,
        }
    )


@router.post("/{league_id}/favourite")
async def toggle_favourite(league_id: int, request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "not logged in"}, status_code=401)
    membership = db.query(models.LeagueMember).filter_by(league_id=league_id, user_id=user.id).first()
    if not membership:
        return JSONResponse({"error": "not a member"}, status_code=404)
    membership.is_favourite = not membership.is_favourite
    db.commit()
    return JSONResponse({"is_favourite": membership.is_favourite})


@router.get("/discover")
async def discover(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    joined_ids = {
        m.league_id for m in db.query(models.LeagueMember)
        .filter(models.LeagueMember.user_id == user.id).all()
    }
    global_leagues = db.query(models.League).filter(
        models.League.is_public == True, models.League.category == "global"
    ).all()
    country_leagues = db.query(models.League).filter(
        models.League.is_public == True, models.League.category == "country"
    ).order_by(models.League.name).all()
    other_public = db.query(models.League).filter(
        models.League.is_public == True, models.League.category == "general"
    ).order_by(models.League.name).all()
    all_discover = global_leagues + country_leagues + other_public
    counts = _member_counts(db, [l.id for l in all_discover])
    return templates.TemplateResponse("leagues/discover.html", {
        "request": request, "user": user,
        "global_leagues": global_leagues,
        "country_leagues": country_leagues,
        "other_public": other_public,
        "joined_ids": joined_ids,
        "member_counts": counts,
    })


@router.post("/{league_id}/join-open")
async def join_open_league(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(
        models.League.id == league_id, models.League.is_public == True
    ).first()
    if not league:
        return RedirectResponse("/leagues/discover", status_code=303)
    existing = db.query(models.LeagueMember).filter(
        models.LeagueMember.league_id == league_id,
        models.LeagueMember.user_id == user.id,
    ).first()
    if not existing:
        db.add(models.LeagueMember(league_id=league_id, user_id=user.id))
        db.commit()
    return RedirectResponse(f"/leagues/{league_id}", status_code=303)


@router.get("/create")
async def create_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("leagues/create.html", {"request": request, "user": user, "error": None})


@router.post("/create")
async def create_league(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    accent_color: str = Form("#1a47c0"),
    badge_emoji: str = Form("🏆"),
    points_exact: int = Form(3),
    points_result: int = Form(1),
    sweepstake: bool = Form(False),
    buy_in: float = Form(10.0),
    teams_per_person: int = Form(1),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    code = _gen_code()
    while db.query(models.League).filter(models.League.invite_code == code).first():
        code = _gen_code()
    league = models.League(
        name=name.strip(),
        description=description.strip()[:200] or None,
        accent_color=accent_color if accent_color.startswith("#") else "#1a47c0",
        badge_emoji=badge_emoji[:6],
        invite_code=code,
        admin_id=user.id,
        points_exact_score=max(0, points_exact),
        points_correct_result=max(0, points_result),
        sweepstake_enabled=sweepstake,
        sweepstake_buy_in=max(0, buy_in),
        sweepstake_teams_per_person=max(1, teams_per_person),
    )
    db.add(league)
    db.flush()
    member = models.LeagueMember(league_id=league.id, user_id=user.id, sweepstake_paid=True)
    db.add(member)
    # Auto-add superadmin to every league
    superadmin = db.query(models.User).filter(models.User.is_superadmin == True).first()
    if superadmin and superadmin.id != user.id:
        db.add(models.LeagueMember(league_id=league.id, user_id=superadmin.id, sweepstake_paid=True))
    db.commit()
    return RedirectResponse(f"/leagues/{league.id}", status_code=303)


@router.get("/join")
async def join_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("leagues/join.html", {"request": request, "user": user, "error": None})


@router.post("/join")
async def join_league(
    request: Request,
    invite_code: str = Form(...),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.invite_code == invite_code.upper().strip()).first()
    if not league:
        return templates.TemplateResponse(
            "leagues/join.html",
            {"request": request, "user": user, "error": "League not found. Check your invite code."},
            status_code=404,
        )
    existing = db.query(models.LeagueMember).filter(
        models.LeagueMember.league_id == league.id,
        models.LeagueMember.user_id == user.id,
    ).first()
    if existing:
        return RedirectResponse(f"/leagues/{league.id}", status_code=303)
    member = models.LeagueMember(league_id=league.id, user_id=user.id)
    db.add(member)
    db.commit()
    return RedirectResponse(f"/leagues/{league.id}", status_code=303)


@router.get("/{league_id}")
async def league_detail(request: Request, league_id: int, db: Session = Depends(get_db)):
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
    if not membership and not user.is_superadmin:
        return RedirectResponse("/leagues", status_code=303)

    leaderboard = _get_leaderboard(league, db)
    upcoming_matches = (
        db.query(models.Match)
        .filter(models.Match.status == "scheduled")
        .order_by(models.Match.match_date)
        .limit(10)
        .all()
    )
    user_preds = {
        p.match_id: p
        for p in db.query(models.Prediction).filter(
            models.Prediction.league_id == league_id,
            models.Prediction.user_id == user.id,
        ).all()
    }
    recent_results = (
        db.query(models.Match)
        .filter(models.Match.status == "finished")
        .order_by(models.Match.match_date.desc())
        .limit(5)
        .all()
    )
    user_bracket_pick = db.query(models.TournamentPick).filter(
        models.TournamentPick.league_id == league_id,
        models.TournamentPick.user_id == user.id,
    ).first()

    # Live sweepstake standings (computed on the fly from finished matches, so always current)
    sweep_lb = []
    if league.sweepstake_enabled and league.sweepstake_drawn:
        from routers.sweepstake import _calc_sweep_points
        sweep_pts = _calc_sweep_points(league, db)
        teams_by_user: dict = {}
        for a in league.sweepstake_assignments:
            teams_by_user.setdefault(a.user_id, []).append(a.team)
        sweep_lb = sorted(
            [
                {"user": m.user, "pts": sweep_pts.get(m.user_id, 0),
                 "teams": teams_by_user.get(m.user_id, [])}
                for m in league.members
            ],
            key=lambda x: x["pts"], reverse=True,
        )

    return templates.TemplateResponse(
        "leagues/detail.html",
        {
            "request": request,
            "user": user,
            "league": league,
            "leaderboard": leaderboard,
            "upcoming_matches": upcoming_matches,
            "user_preds": user_preds,
            "recent_results": recent_results,
            "is_admin": league.admin_id == user.id or user.is_superadmin,
            "user_bracket_pick": user_bracket_pick,
            "sweep_lb": sweep_lb,
            "now": datetime.utcnow(),
        },
    )


@router.get("/{league_id}/settings")
async def settings_page(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id and not user.is_superadmin:
        return RedirectResponse(f"/leagues/{league_id}", status_code=303)
    return templates.TemplateResponse(
        "leagues/settings.html", {"request": request, "user": user, "league": league, "error": None, "success": None}
    )


@router.post("/{league_id}/settings")
async def update_settings(
    request: Request,
    league_id: int,
    name: str = Form(...),
    description: str = Form(""),
    accent_color: str = Form("#1a47c0"),
    badge_emoji: str = Form("🏆"),
    is_public: bool = Form(False),
    points_exact: int = Form(3),
    points_result: int = Form(1),
    points_bracket_winner: int = Form(10),
    points_bracket_finalist: int = Form(5),
    points_bracket_semi: int = Form(2),
    points_bracket_quarter: int = Form(1),
    sweepstake: bool = Form(False),
    buy_in: float = Form(10.0),
    teams_per_person: int = Form(1),
    boost_multiplier: int = Form(2),
    sweep_pts_win: int = Form(2),
    sweep_pts_draw: int = Form(0),
    sweep_pts_goal: int = Form(0),
    sweep_pts_clean_sheet: int = Form(0),
    sweep_big_win_threshold: int = Form(0),
    sweep_big_win_pts: int = Form(0),
    sweep_upset_pts: int = Form(0),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id and not user.is_superadmin:
        return RedirectResponse(f"/leagues/{league_id}", status_code=303)
    league.name = name.strip()
    league.description = description.strip()[:200] or None
    league.accent_color = accent_color if accent_color.startswith("#") else "#1a47c0"
    league.badge_emoji = badge_emoji[:6]
    if league.category == "general":       # don't override system league settings
        league.is_public = is_public
    league.points_exact_score = max(0, points_exact)
    league.points_correct_result = max(0, points_result)
    league.points_bracket_winner = max(0, points_bracket_winner)
    league.points_bracket_finalist = max(0, points_bracket_finalist)
    league.points_bracket_semi = max(0, points_bracket_semi)
    league.points_bracket_quarter = max(0, points_bracket_quarter)
    league.sweepstake_enabled = sweepstake
    league.sweepstake_buy_in = max(0, buy_in)
    league.sweepstake_teams_per_person = max(1, teams_per_person)
    league.boost_multiplier = max(2, boost_multiplier)
    league.sweep_pts_win = max(0, sweep_pts_win)
    league.sweep_pts_draw = max(0, sweep_pts_draw)
    league.sweep_pts_goal = max(0, sweep_pts_goal)
    league.sweep_pts_clean_sheet = max(0, sweep_pts_clean_sheet)
    league.sweep_big_win_threshold = max(0, sweep_big_win_threshold)
    league.sweep_big_win_pts = max(0, sweep_big_win_pts)
    league.sweep_upset_pts = max(0, sweep_upset_pts)
    db.commit()
    return templates.TemplateResponse(
        "leagues/settings.html",
        {"request": request, "user": user, "league": league, "error": None, "success": "Settings saved!"},
    )


@router.post("/{league_id}/banner")
async def upload_banner(
    request: Request,
    league_id: int,
    banner: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id and not user.is_superadmin:
        return RedirectResponse(f"/leagues/{league_id}/settings", status_code=303)

    ext = os.path.splitext(banner.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        return templates.TemplateResponse(
            "leagues/settings.html",
            {"request": request, "user": user, "league": league,
             "error": "Image must be JPG, PNG, WebP, or GIF", "success": None},
            status_code=400,
        )

    data = await banner.read()
    if len(data) > MAX_SIZE:
        return templates.TemplateResponse(
            "leagues/settings.html",
            {"request": request, "user": user, "league": league,
             "error": "File too large (max 10 MB)", "success": None},
            status_code=400,
        )

    data, ext = process_image(data, "banner")
    os.makedirs(LEAGUE_UPLOAD_DIR, exist_ok=True)
    filename = f"{league_id}_{uuid.uuid4().hex[:8]}{ext}"
    path = os.path.join(LEAGUE_UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)

    if league.banner_url:
        old = os.path.join(LEAGUE_UPLOAD_DIR, os.path.basename(league.banner_url))
        try:
            os.remove(old)
        except OSError:
            pass

    league.banner_url = f"/static/uploads/leagues/{filename}"
    db.commit()
    return RedirectResponse(f"/leagues/{league_id}/settings", status_code=303)


LOGO_UPLOAD_DIR = os.path.join(_uploads_base, "leagues", "logos")


@router.post("/{league_id}/logo")
async def upload_logo(
    request: Request,
    league_id: int,
    logo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id and not user.is_superadmin:
        return RedirectResponse(f"/leagues/{league_id}/settings", status_code=303)
    ext = os.path.splitext(logo.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        return RedirectResponse(f"/leagues/{league_id}/settings?err=type", status_code=303)
    data = await logo.read()
    if len(data) > MAX_SIZE:
        return RedirectResponse(f"/leagues/{league_id}/settings?err=size", status_code=303)
    data, ext = process_image(data, "avatar")   # square crop, 400×400
    os.makedirs(LOGO_UPLOAD_DIR, exist_ok=True)
    filename = f"{league_id}_{uuid.uuid4().hex[:8]}{ext}"
    with open(os.path.join(LOGO_UPLOAD_DIR, filename), "wb") as f:
        f.write(data)
    if league.logo_url:
        try:
            old = os.path.join(LOGO_UPLOAD_DIR, os.path.basename(league.logo_url))
            os.remove(old)
        except OSError:
            pass
    league.logo_url = f"/static/uploads/leagues/logos/{filename}"
    db.commit()
    return RedirectResponse(f"/leagues/{league_id}/settings", status_code=303)


@router.post("/{league_id}/nickname")
async def set_nickname(
    request: Request,
    league_id: int,
    nickname: str = Form(""),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    member = db.query(models.LeagueMember).filter(
        models.LeagueMember.league_id == league_id,
        models.LeagueMember.user_id == user.id,
    ).first()
    if member:
        member.nickname = nickname.strip()[:50] or None
        db.commit()
    return RedirectResponse(f"/leagues/{league_id}", status_code=303)


@router.post("/{league_id}/members/{member_user_id}/points")
async def adjust_member_points(
    request: Request,
    league_id: int,
    member_user_id: int,
    action: str = Form(...),          # "add" | "sub" | "set"
    amount: int = Form(0),
    db: Session = Depends(get_db),
):
    """League admin grants/adjusts manual bonus points for a member (e.g. late-joiner catch-up)."""
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or (league.admin_id != user.id and not user.is_superadmin):
        return RedirectResponse(f"/leagues/{league_id}", status_code=303)
    member = db.query(models.LeagueMember).filter(
        models.LeagueMember.league_id == league_id,
        models.LeagueMember.user_id == member_user_id,
    ).first()
    if member:
        current = member.bonus_points or 0
        if action == "set":
            member.bonus_points = amount
        elif action == "add":
            member.bonus_points = current + amount
        elif action == "sub":
            member.bonus_points = current - amount
        db.commit()
    return RedirectResponse(f"/leagues/{league_id}", status_code=303)


@router.post("/{league_id}/banner/remove")
async def remove_banner(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id and not user.is_superadmin:
        return RedirectResponse(f"/leagues/{league_id}/settings", status_code=303)
    if league.banner_url:
        old = os.path.join(LEAGUE_UPLOAD_DIR, os.path.basename(league.banner_url))
        try:
            os.remove(old)
        except OSError:
            pass
        league.banner_url = None
        db.commit()
    return RedirectResponse(f"/leagues/{league_id}/settings", status_code=303)
