import sys, os, asyncio
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from datetime import datetime
from markupsafe import Markup

from database import engine, Base, get_db
import models
import auth
from routers import auth as auth_router, leagues, predictions, sweepstake, matches, admin, bracket, standings, profile, markets, teams
from services import results_fetcher

# ── Flag image helpers ──────────────────────────────────────
CODE_TO_ISO2 = {
    "MEX": "mx",  "RSA": "za",  "KOR": "kr",  "CZE": "cz",
    "CAN": "ca",  "BIH": "ba",  "QAT": "qa",  "SUI": "ch",
    "BRA": "br",  "MAR": "ma",  "HAI": "ht",  "SCO": "gb-sct",
    "USA": "us",  "PAR": "py",  "AUS": "au",  "TUR": "tr",
    "GER": "de",  "CUW": "cw",  "CIV": "ci",  "ECU": "ec",
    "NED": "nl",  "JPN": "jp",  "SWE": "se",  "TUN": "tn",
    "BEL": "be",  "EGY": "eg",  "IRN": "ir",  "NZL": "nz",
    "ESP": "es",  "CPV": "cv",  "KSA": "sa",  "URU": "uy",
    "FRA": "fr",  "SEN": "sn",  "IRQ": "iq",  "NOR": "no",
    "ARG": "ar",  "ALG": "dz",  "AUT": "at",  "JOR": "jo",
    "POR": "pt",  "COD": "cd",  "UZB": "uz",  "COL": "co",
    "ENG": "gb-eng", "CRO": "hr", "GHA": "gh", "PAN": "pa",
}

def flag_url(code: str) -> str:
    iso2 = CODE_TO_ISO2.get(code, code.lower()[:2])
    return f"https://flagcdn.com/{iso2}.svg"

def flag_img(code: str, cls: str = "flag flag-md") -> Markup:
    url = flag_url(code)
    return Markup(f'<img src="{url}" class="{cls}" alt="{code}" loading="lazy">')

_HEX_RE = __import__("re").compile(r"^#[0-9a-fA-F]{3,8}$")

def avatar_html(user, size: str = "md") -> Markup:
    from markupsafe import escape
    raw_color = getattr(user, "avatar_color", "#1a47c0") or "#1a47c0"
    color = raw_color if _HEX_RE.match(raw_color) else "#1a47c0"
    name = getattr(user, "display_name", None) or getattr(user, "username", "?") or "?"
    initial = escape(name[0].upper())
    fallback = f"this.replaceWith(Object.assign(document.createElement('div'),{{className:'avatar avatar-{size}',style:'background:{color};font-family:sans-serif;font-weight:700',textContent:'{initial}'}}))"
    img_url = getattr(user, "avatar_img_url", None)
    if img_url:
        safe_url = escape(img_url)
        return Markup(
            f'<img src="{safe_url}" class="avatar avatar-{size}" style="object-fit:cover" alt="" onerror="{fallback}">'
        )
    return Markup(
        f'<div class="avatar avatar-{size}" style="background:{color};font-family:sans-serif;font-weight:700">{initial}</div>'
    )


def _migrate_db():
    """Add columns that didn't exist in older DB versions."""
    import sqlite3
    db_url = str(engine.url)
    if not db_url.startswith("sqlite"):
        return
    path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    if not path or path == ":memory:":
        return  # in-memory test DB — create_all handles schema, no migration needed
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    migrations = [
        ("users", "profile_bg", "VARCHAR(100)"),
        ("users", "profile_banner_url", "VARCHAR(200)"),
        ("league_members", "nickname", "VARCHAR(50)"),
        ("leagues", "logo_url", "VARCHAR(200)"),
        ("leagues", "is_public", "BOOLEAN DEFAULT 0"),
        ("leagues", "category", "VARCHAR(20) DEFAULT 'general'"),
        ("predictions", "boosted", "BOOLEAN DEFAULT 0"),
        ("league_members", "is_favourite", "BOOLEAN DEFAULT 0"),
    ]
    for table, col, col_type in migrations:
        existing = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
        if col not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()


def _seed_public_leagues():
    """Create the global league and country fan leagues if they don't exist yet."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.is_superadmin == True).first()
        if not admin:
            return

        # Global league
        if not db.query(models.League).filter(models.League.category == "global").first():
            gl = models.League(
                name="World Cup 2026 Global",
                invite_code="WC2026GL",
                admin_id=admin.id,
                description="The main global prediction league — anyone can join.",
                accent_color="#f5a623",
                badge_emoji="W",
                is_public=True,
                category="global",
            )
            db.add(gl)

        # Country fan leagues — one per WC team
        teams = db.query(models.Team).all()
        existing_codes = {
            r[0] for r in db.query(models.League.invite_code)
            .filter(models.League.category == "country").all()
        }
        for team in teams:
            code = f"FAN{team.code}"
            if code not in existing_codes:
                db.add(models.League(
                    name=f"{team.name} Fans",
                    invite_code=code,
                    admin_id=admin.id,
                    description=f"Public league for fans of {team.name}.",
                    accent_color="#1a47c0",
                    badge_emoji=team.code,
                    is_public=True,
                    category="country",
                ))
        db.commit()

        # Ensure admin is a member of every league
        all_leagues = db.query(models.League).all()
        for league in all_leagues:
            exists = db.query(models.LeagueMember).filter_by(
                league_id=league.id, user_id=admin.id
            ).first()
            if not exists:
                db.add(models.LeagueMember(league_id=league.id, user_id=admin.id, sweepstake_paid=True))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate_db()
    _seed_public_leagues()
    task = asyncio.create_task(results_fetcher.results_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan, title="World Cup 2026 Predictor", docs_url=None, redoc_url=None)

_static_dir = os.path.join(os.path.dirname(__file__), "static")
_uploads_dir = os.getenv("UPLOADS_DIR", os.path.join(_static_dir, "uploads"))
for _sub in ("avatars", "videos", "leagues", "markets"):
    os.makedirs(os.path.join(_uploads_dir, _sub), exist_ok=True)

# Uploads served first so persistent-volume files take precedence over ephemeral /static/uploads/
app.mount("/static/uploads", StaticFiles(directory=_uploads_dir), name="uploads")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

from shared import templates  # shared singleton used by all routers
from translations import t as _t

# Register template globals on the shared instance
templates.env.globals["flag_url"] = flag_url
templates.env.globals["flag_img"] = flag_img
templates.env.globals["avatar_html"] = avatar_html
templates.env.globals["AVATAR_COLORS"] = models.AVATAR_COLORS
templates.env.globals["AVATAR_ICONS"] = models.AVATAR_ICONS
templates.env.globals["t"] = _t

from routers.admin import _active_video_url
templates.env.globals["bg_video_url"] = _active_video_url

app.include_router(auth_router.router)
app.include_router(leagues.router)
app.include_router(predictions.router)
app.include_router(sweepstake.router)
app.include_router(matches.router)
app.include_router(admin.router)
app.include_router(bracket.router)
app.include_router(standings.router)
app.include_router(profile.router)
app.include_router(markets.router)
app.include_router(teams.router)


@app.get("/")
async def index(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    upcoming = (
        db.query(models.Match)
        .filter(models.Match.status == "scheduled")
        .order_by(models.Match.match_date)
        .limit(6)
        .all()
    )
    user_leagues = []
    fav_ids = set()
    has_favourites = False
    if user:
        memberships = db.query(models.LeagueMember).filter(models.LeagueMember.user_id == user.id).all()
        all_leagues = [m.league for m in memberships]
        fav_ids = {m.league_id for m in memberships if m.is_favourite}
        has_favourites = bool(fav_ids)
        user_leagues = [l for l in all_leagues if l.id in fav_ids] if has_favourites else all_leagues

    # Countdown to first match
    first_match = db.query(models.Match).order_by(models.Match.match_date).first()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request, "user": user,
            "upcoming": upcoming, "user_leagues": user_leagues,
            "fav_ids": fav_ids,
            "has_favourites": has_favourites,
            "now": datetime.utcnow(),
            "first_match": first_match,
        },
    )


@app.post("/set-language")
async def set_language(
    request: Request,
    lang: str = Form("en"),
    db: Session = Depends(get_db),
):
    lang = lang if lang in ("en", "pt") else "en"
    referer = request.headers.get("referer", "/")
    response = RedirectResponse(referer, status_code=303)
    response.set_cookie("lang", lang, max_age=365 * 24 * 3600, samesite="lax")
    user = auth.get_current_user(request, db)
    if user and hasattr(user, "language"):
        user.language = lang
        db.commit()
    return response
