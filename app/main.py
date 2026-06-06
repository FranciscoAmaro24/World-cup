import sys, os, asyncio
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from datetime import datetime
from markupsafe import Markup

from database import engine, Base, get_db
import models
import auth
from routers import auth as auth_router, leagues, predictions, sweepstake, matches, admin, bracket, standings, profile, markets
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
    img_url = getattr(user, "avatar_img_url", None)
    if img_url:
        safe_url = escape(img_url)
        return Markup(
            f'<img src="{safe_url}" class="avatar avatar-{size}" style="object-fit:cover" alt="">'
        )
    raw_color = getattr(user, "avatar_color", "#1a47c0") or "#1a47c0"
    # Whitelist: must be a valid CSS hex colour
    color = raw_color if _HEX_RE.match(raw_color) else "#1a47c0"
    icon = escape(getattr(user, "avatar_icon", "⚽") or "⚽")
    return Markup(
        f'<div class="avatar avatar-{size}" style="background:{color}">{icon}</div>'
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(results_fetcher.results_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan, title="World Cup 2026 Predictor", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

from shared import templates  # shared singleton used by all routers

# Register template globals on the shared instance
templates.env.globals["flag_url"] = flag_url
templates.env.globals["flag_img"] = flag_img
templates.env.globals["avatar_html"] = avatar_html
templates.env.globals["AVATAR_COLORS"] = models.AVATAR_COLORS
templates.env.globals["AVATAR_ICONS"] = models.AVATAR_ICONS

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
    if user:
        memberships = db.query(models.LeagueMember).filter(models.LeagueMember.user_id == user.id).all()
        user_leagues = [m.league for m in memberships]

    # Countdown to first match
    first_match = db.query(models.Match).order_by(models.Match.match_date).first()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request, "user": user,
            "upcoming": upcoming, "user_leagues": user_leagues,
            "now": datetime.utcnow(),
            "first_match": first_match,
        },
    )
