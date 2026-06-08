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
        password_hash=auth.hash_password(password),
        is_superadmin=is_first,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    token = auth.create_access_token(new_user.id)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("access_token", token, httponly=True, samesite="lax", max_age=604800)
    return response


@router.post("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("access_token")
    return response
