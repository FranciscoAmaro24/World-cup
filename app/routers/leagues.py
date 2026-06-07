import random
import string
import uuid
import os
from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session

from database import get_db
import models
import auth
from shared import templates
from image_utils import process_image

_uploads_base = os.getenv("UPLOADS_DIR", os.path.join(os.path.dirname(__file__), "..", "static", "uploads"))
LEAGUE_UPLOAD_DIR = os.path.join(_uploads_base, "leagues")
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE = 10 * 1024 * 1024

router = APIRouter(prefix="/leagues")


def _gen_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _get_leaderboard(league: models.League, db: Session):
    members = league.members
    rows = []
    for m in members:
        preds = db.query(models.Prediction).filter(
            models.Prediction.league_id == league.id,
            models.Prediction.user_id == m.user_id,
            models.Prediction.points_awarded.isnot(None),
        ).all()
        match_pts = sum(p.points_awarded for p in preds)
        bracket_pick = db.query(models.TournamentPick).filter(
            models.TournamentPick.league_id == league.id,
            models.TournamentPick.user_id == m.user_id,
        ).first()
        bracket_pts = bracket_pick.points_awarded if bracket_pick else 0
        rows.append({
            "user": m.user,
            "member": m,
            "points": match_pts + bracket_pts,
            "match_points": match_pts,
            "bracket_points": bracket_pts,
            "predictions": len(preds),
            "has_bracket": bracket_pick is not None,
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
    user_leagues = [m.league for m in memberships]
    return templates.TemplateResponse(
        "leagues/list.html", {"request": request, "user": user, "leagues": user_leagues}
    )


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
    if not membership:
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
            "is_admin": league.admin_id == user.id,
            "user_bracket_pick": user_bracket_pick,
            "now": datetime.utcnow(),
        },
    )


@router.get("/{league_id}/settings")
async def settings_page(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id:
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
    points_exact: int = Form(3),
    points_result: int = Form(1),
    points_bracket_winner: int = Form(10),
    points_bracket_finalist: int = Form(5),
    points_bracket_semi: int = Form(2),
    points_bracket_quarter: int = Form(1),
    sweepstake: bool = Form(False),
    buy_in: float = Form(10.0),
    teams_per_person: int = Form(1),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id:
        return RedirectResponse(f"/leagues/{league_id}", status_code=303)
    league.name = name.strip()
    league.description = description.strip()[:200] or None
    league.accent_color = accent_color if accent_color.startswith("#") else "#1a47c0"
    league.badge_emoji = badge_emoji[:6]
    league.points_exact_score = max(0, points_exact)
    league.points_correct_result = max(0, points_result)
    league.points_bracket_winner = max(0, points_bracket_winner)
    league.points_bracket_finalist = max(0, points_bracket_finalist)
    league.points_bracket_semi = max(0, points_bracket_semi)
    league.points_bracket_quarter = max(0, points_bracket_quarter)
    league.sweepstake_enabled = sweepstake
    league.sweepstake_buy_in = max(0, buy_in)
    league.sweepstake_teams_per_person = max(1, teams_per_person)
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
    if not league or league.admin_id != user.id:
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
        old = os.path.join(os.path.dirname(__file__), "..", "static", league.banner_url.lstrip("/"))
        try:
            os.remove(old)
        except OSError:
            pass

    league.banner_url = f"/static/uploads/leagues/{filename}"
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


@router.post("/{league_id}/banner/remove")
async def remove_banner(request: Request, league_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    if not league or league.admin_id != user.id:
        return RedirectResponse(f"/leagues/{league_id}/settings", status_code=303)
    if league.banner_url:
        old = os.path.join(os.path.dirname(__file__), "..", "static", league.banner_url.lstrip("/"))
        try:
            os.remove(old)
        except OSError:
            pass
        league.banner_url = None
        db.commit()
    return RedirectResponse(f"/leagues/{league_id}/settings", status_code=303)
