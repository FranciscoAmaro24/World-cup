import os
import uuid
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session

from database import get_db
import models
import auth
from shared import templates
from image_utils import process_image

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "avatars")
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE = 10 * 1024 * 1024

router = APIRouter()


def _user_stats(user: models.User, db: Session) -> dict:
    preds = db.query(models.Prediction).filter(
        models.Prediction.user_id == user.id,
        models.Prediction.points_awarded.isnot(None),
    ).all()
    total_pts = sum(p.points_awarded for p in preds)
    exact = sum(1 for p in preds if p.match and p.home_score_pred == p.match.home_score and p.away_score_pred == p.match.away_score)
    correct = sum(1 for p in preds if p.points_awarded and p.points_awarded > 0)
    accuracy = round(correct / len(preds) * 100) if preds else 0
    leagues_count = db.query(models.LeagueMember).filter(models.LeagueMember.user_id == user.id).count()
    return {
        "total_pts": total_pts,
        "predictions": len(preds),
        "exact": exact,
        "correct": correct,
        "accuracy": accuracy,
        "leagues": leagues_count,
    }


@router.get("/profile")
async def my_profile(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse(f"/profile/{user.username}", status_code=303)


@router.get("/profile/edit")
async def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    teams = db.query(models.Team).order_by(models.Team.group_letter, models.Team.name).all()
    return templates.TemplateResponse(
        "profile/edit.html",
        {"request": request, "user": user, "teams": teams, "error": None, "success": None},
    )


@router.post("/profile/edit")
async def save_profile(
    request: Request,
    display_name: str = Form(""),
    bio: str = Form(""),
    avatar_color: str = Form("#1a47c0"),
    avatar_icon: str = Form("⚽"),
    favorite_team_id: int = Form(0),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    user.display_name = display_name.strip()[:50] or None
    user.bio = bio.strip()[:120] or None
    user.avatar_color = avatar_color if avatar_color.startswith("#") else "#1a47c0"
    user.avatar_icon = avatar_icon[:6]
    user.favorite_team_id = favorite_team_id if favorite_team_id > 0 else None
    db.commit()
    teams = db.query(models.Team).order_by(models.Team.group_letter, models.Team.name).all()
    return templates.TemplateResponse(
        "profile/edit.html",
        {"request": request, "user": user, "teams": teams, "error": None, "success": "Profile saved!"},
    )


@router.post("/profile/avatar")
async def upload_avatar(
    request: Request,
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    ext = os.path.splitext(avatar.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        teams = db.query(models.Team).order_by(models.Team.group_letter, models.Team.name).all()
        return templates.TemplateResponse(
            "profile/edit.html",
            {"request": request, "user": user, "teams": teams,
             "error": "Image must be JPG, PNG, WebP, or GIF", "success": None},
            status_code=400,
        )

    data = await avatar.read()
    if len(data) > MAX_SIZE:
        teams = db.query(models.Team).order_by(models.Team.group_letter, models.Team.name).all()
        return templates.TemplateResponse(
            "profile/edit.html",
            {"request": request, "user": user, "teams": teams,
             "error": "File too large (max 10 MB)", "success": None},
            status_code=400,
        )

    data, ext = process_image(data, "avatar")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)

    # Delete old avatar file if present
    if user.avatar_img_url:
        old_file = os.path.join(os.path.dirname(__file__), "..", "static", user.avatar_img_url.lstrip("/"))
        try:
            os.remove(old_file)
        except OSError:
            pass

    user.avatar_img_url = f"/static/uploads/avatars/{filename}"
    db.commit()
    return RedirectResponse("/profile/edit", status_code=303)


@router.post("/profile/avatar/remove")
async def remove_avatar(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if user.avatar_img_url:
        old_file = os.path.join(os.path.dirname(__file__), "..", "static", user.avatar_img_url.lstrip("/"))
        try:
            os.remove(old_file)
        except OSError:
            pass
        user.avatar_img_url = None
        db.commit()
    return RedirectResponse("/profile/edit", status_code=303)


@router.get("/profile/{username}")
async def view_profile(request: Request, username: str, db: Session = Depends(get_db)):
    viewer = auth.get_current_user(request, db)
    target = db.query(models.User).filter(models.User.username == username).first()
    if not target:
        return RedirectResponse("/", status_code=303)
    stats = _user_stats(target, db)
    memberships = db.query(models.LeagueMember).filter(models.LeagueMember.user_id == target.id).all()
    leagues = [m.league for m in memberships]
    recent_preds = (
        db.query(models.Prediction)
        .filter(models.Prediction.user_id == target.id, models.Prediction.points_awarded.isnot(None))
        .order_by(models.Prediction.submitted_at.desc())
        .limit(5)
        .all()
    )
    return templates.TemplateResponse(
        "profile/view.html",
        {
            "request": request,
            "user": viewer,
            "target": target,
            "stats": stats,
            "leagues": leagues,
            "recent_preds": recent_preds,
            "is_own": viewer and viewer.id == target.id,
        },
    )
