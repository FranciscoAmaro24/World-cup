from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session
import re

from database import get_db
import models
import auth
from shared import templates

router = APIRouter()

_BANNED_WORDS = {
    "nigger", "nigga", "nigg", "n1gger", "n1gga",
    "faggot", "fagg0t", "fag", "tranny",
    "chink", "spic", "spick", "kike", "gook", "wetback",
    "retard", "retarded",
    "cunt", "cünт",
}

def _contains_banned_word(text: str) -> bool:
    normalised = re.sub(r"[^a-z0-9]", "", text.lower())
    return any(w in normalised for w in _BANNED_WORDS)


def _normalise_phrase(phrase: str) -> str:
    """Case/whitespace-insensitive so users can recover without exact-matching their phrase."""
    return re.sub(r"\s+", " ", phrase.strip().lower())


def _hash_recovery(phrase: str) -> str | None:
    phrase = _normalise_phrase(phrase)
    return auth.hash_password(phrase) if phrase else None


@router.get("/login")
async def login_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "user": None, "error": None})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not auth.verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "user": None, "error": "Invalid username or password"},
            status_code=401,
        )
    token = auth.create_access_token(user.id)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=604800)
    return response


@router.get("/forgot-password")
async def forgot_password_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        "forgot_password.html", {"request": request, "user": None, "error": None, "success": None}
    )


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    username: str = Form(...),
    recovery_phrase: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    def fail(msg: str):
        return templates.TemplateResponse(
            "forgot_password.html",
            {"request": request, "user": None, "error": msg, "success": None},
            status_code=400,
        )

    if len(new_password) < 6:
        return fail("New password must be at least 6 characters")

    user = db.query(models.User).filter(models.User.username == username).first()
    phrase = _normalise_phrase(recovery_phrase)
    # Same error whether the user exists or the phrase is wrong — don't leak which.
    if not user or not user.recovery_phrase_hash or not auth.verify_password(phrase, user.recovery_phrase_hash):
        return fail("Username and recovery phrase do not match")

    user.password_hash = auth.hash_password(new_password)
    db.commit()
    return templates.TemplateResponse(
        "forgot_password.html",
        {"request": request, "user": None, "error": None,
         "success": "Password updated — you can now log in with your new password."},
    )


@router.get("/reset-password/{token}")
async def reset_password_page(request: Request, token: str, db: Session = Depends(get_db)):
    target = auth.verify_reset_token(token, db)
    if not target:
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "user": None, "token": token, "target": None,
             "error": "This reset link is invalid or has expired. Ask an admin for a new one.", "success": None},
            status_code=400,
        )
    return templates.TemplateResponse(
        "reset_password.html",
        {"request": request, "user": None, "token": token, "target": target, "error": None, "success": None},
    )


@router.post("/reset-password/{token}")
async def reset_password(
    request: Request,
    token: str,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    target = auth.verify_reset_token(token, db)
    if not target:
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "user": None, "token": token, "target": None,
             "error": "This reset link is invalid or has expired. Ask an admin for a new one.", "success": None},
            status_code=400,
        )
    if len(new_password) < 6:
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "user": None, "token": token, "target": target,
             "error": "Password must be at least 6 characters", "success": None},
            status_code=400,
        )
    target.password_hash = auth.hash_password(new_password)
    db.commit()  # password change invalidates the token (it was signed with the old hash)
    return templates.TemplateResponse(
        "reset_password.html",
        {"request": request, "user": None, "token": token, "target": None,
         "error": None, "success": "Password updated — you can now log in with your new password."},
    )


@router.get("/register")
async def register_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request, "user": None, "error": None})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    recovery_phrase: str = Form(""),
    db: Session = Depends(get_db),
):
    if len(username) < 3 or len(username) > 30:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "user": None, "error": "Username must be 3–30 characters"},
            status_code=400,
        )
    if _contains_banned_word(username):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "user": None, "error": "ahahaha very funny, choose smth else pls"},
            status_code=400,
        )
    if len(password) < 6:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "user": None, "error": "Password must be at least 6 characters"},
            status_code=400,
        )
    if db.query(models.User).filter(models.User.username == username).first():
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "user": None, "error": "Username already taken"},
            status_code=400,
        )
    is_first = db.query(models.User).count() == 0
    new_user = models.User(
        username=username,
        email=f"_noemail.{username}@wc2026",
        password_hash=auth.hash_password(password),
        recovery_phrase_hash=_hash_recovery(recovery_phrase),
        is_superadmin=is_first,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Auto-enroll into the global league so everyone shows on the entire leaderboard
    global_league = db.query(models.League).filter(models.League.category == "global").first()
    if global_league:
        db.add(models.LeagueMember(league_id=global_league.id, user_id=new_user.id))
        db.commit()

    token = auth.create_access_token(new_user.id)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=604800)
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response
