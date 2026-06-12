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


def _sqlite_path() -> str | None:
    """Return the on-disk SQLite file path, or None for non-file DBs (e.g. in-memory / non-sqlite)."""
    db_url = str(engine.url)
    if not db_url.startswith("sqlite"):
        return None
    path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    if not path or path == ":memory:":
        return None
    return path


def _backup_db(keep: int = 20):
    """Snapshot the SQLite DB before migrations run, so no data is lost on a bad upgrade.

    Uses SQLite's online backup API (safe with the file open), writes a timestamped
    copy into a `backups/` folder next to the DB, and prunes to the most recent `keep`.
    """
    import sqlite3
    import glob
    path = _sqlite_path()
    if not path or not os.path.exists(path):
        return  # nothing to back up yet (fresh DB)

    backup_dir = os.path.join(os.path.dirname(path) or ".", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(backup_dir, f"worldcup-{stamp}.db")

    try:
        src = sqlite3.connect(path)
        dst = sqlite3.connect(dest)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
        print(f"[backup] DB snapshot written to {dest} ({os.path.getsize(dest)} bytes)")
    except Exception as e:
        print(f"[backup] WARNING: DB backup failed: {e}")
        return

    # Prune old backups, keeping the most recent `keep`
    snaps = sorted(glob.glob(os.path.join(backup_dir, "worldcup-*.db")))
    for old in snaps[:-keep]:
        try:
            os.remove(old)
        except OSError:
            pass


def _migrate_db():
    """Add columns that didn't exist in older DB versions."""
    import sqlite3
    path = _sqlite_path()
    if not path:
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
        ("leagues", "boost_multiplier", "INTEGER DEFAULT 2"),
        ("leagues", "sweep_pts_win", "INTEGER DEFAULT 2"),
        ("leagues", "sweep_pts_draw", "INTEGER DEFAULT 0"),
        ("leagues", "sweep_pts_goal", "INTEGER DEFAULT 0"),
        ("leagues", "sweep_pts_clean_sheet", "INTEGER DEFAULT 0"),
        ("leagues", "sweep_big_win_threshold", "INTEGER DEFAULT 0"),
        ("leagues", "sweep_big_win_pts", "INTEGER DEFAULT 0"),
        ("leagues", "sweep_upset_pts", "INTEGER DEFAULT 0"),
        ("sweepstake_groups", "pts_win", "INTEGER"),
        ("sweepstake_assignments", "group_id", "INTEGER"),
        ("users", "main_league_id", "INTEGER"),
    ]
    for table, col, col_type in migrations:
        existing = [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]
        if col not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
    conn.commit()

    # Repair: a previous migration used SELECT * which positionally swapped
    # created_at and avatar_img_url on DBs with a different original column order.
    row = cur.execute("SELECT created_at FROM users WHERE created_at IS NOT NULL LIMIT 1").fetchone()
    if row and row[0] and str(row[0]).startswith("/"):
        cur.execute("UPDATE users SET created_at = avatar_img_url, avatar_img_url = created_at")
        conn.commit()

    # Fill null credits (ALTER TABLE DEFAULT isn't applied to existing rows in SQLite)
    cur.execute("UPDATE users SET credits = 10.0 WHERE credits IS NULL")

    # Remove auto-memberships: superadmin should not be a member of global/country leagues
    cur.execute("""
        DELETE FROM league_members
        WHERE user_id = (SELECT id FROM users WHERE is_superadmin = 1 ORDER BY id LIMIT 1)
        AND league_id IN (SELECT id FROM leagues WHERE category IN ('global', 'country'))
    """)

    # Delete test/bot users by username
    for bot in ("kikokiko",):
        cur.execute("DELETE FROM league_members WHERE user_id = (SELECT id FROM users WHERE username = ?)", (bot,))
        cur.execute("DELETE FROM predictions   WHERE user_id = (SELECT id FROM users WHERE username = ?)", (bot,))
        cur.execute("DELETE FROM tournament_picks WHERE user_id = (SELECT id FROM users WHERE username = ?)", (bot,))
        cur.execute("DELETE FROM sweepstake_assignments WHERE user_id = (SELECT id FROM users WHERE username = ?)", (bot,))
        cur.execute("DELETE FROM users WHERE username = ?", (bot,))

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
    finally:
        db.close()


def _enroll_all_in_global():
    """Make every user a member of the global league so the entire leaderboard shows everyone.

    Idempotent. Runs before the prediction backfill so each user's predictions get replicated
    into (and scored for) the global league.
    """
    from database import SessionLocal
    db = SessionLocal()
    try:
        global_league = db.query(models.League).filter(models.League.category == "global").first()
        if not global_league:
            return
        existing = {
            m.user_id for m in db.query(models.LeagueMember)
            .filter(models.LeagueMember.league_id == global_league.id).all()
        }
        for u in db.query(models.User).all():
            if u.id not in existing:
                db.add(models.LeagueMember(league_id=global_league.id, user_id=u.id))
        db.commit()
    finally:
        db.close()


def _backfill_and_rescore_predictions():
    """Unify historical predictions across every league a user belongs to, and (re)score finished matches.

    Idempotent. For each (user, match) it takes the latest-submitted prediction as canonical,
    ensures a row exists in *every* league the user is a member of (including the global league),
    and recomputes points_awarded for matches that have already finished, using each league's
    own scoring config. Existing rows keep their `boosted` flag; new replica rows are unboosted.
    """
    from database import SessionLocal
    from routers.predictions import calculate_points
    db = SessionLocal()
    try:
        all_preds = db.query(models.Prediction).all()

        # Canonical prediction per (user, match): latest submitted wins
        canonical: dict = {}
        for p in all_preds:
            key = (p.user_id, p.match_id)
            cur = canonical.get(key)
            if cur is None or (p.submitted_at and (not cur.submitted_at or p.submitted_at > cur.submitted_at)):
                canonical[key] = p

        memberships: dict = {}
        for m in db.query(models.LeagueMember).all():
            memberships.setdefault(m.user_id, set()).add(m.league_id)

        matches = {mt.id: mt for mt in db.query(models.Match).all()}
        leagues = {l.id: l for l in db.query(models.League).all()}
        existing = {(p.user_id, p.match_id, p.league_id): p for p in all_preds}

        for (uid, mid), src in canonical.items():
            match = matches.get(mid)
            for lid in memberships.get(uid, set()):
                league = leagues.get(lid)
                if not league:
                    continue
                row = existing.get((uid, mid, lid))
                if row is None:
                    row = models.Prediction(
                        user_id=uid,
                        match_id=mid,
                        league_id=lid,
                        home_score_pred=src.home_score_pred,
                        away_score_pred=src.away_score_pred,
                        boosted=False,
                        submitted_at=src.submitted_at,
                    )
                    db.add(row)
                    existing[(uid, mid, lid)] = row
                # Score (or re-score) matches that have already finished
                if match and match.status == "finished" and match.home_score is not None:
                    row.points_awarded = calculate_points(row, match, league)

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _backup_db()                       # snapshot BEFORE any migration mutates data
    _migrate_db()
    _seed_public_leagues()
    _enroll_all_in_global()
    _backfill_and_rescore_predictions()
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
    from routers.leagues import _member_counts
    counts = _member_counts(db, [l.id for l in user_leagues])

    # User's predictions for upcoming matches (any league — predictions are now unified)
    user_predictions: dict[int, models.Prediction] = {}
    if user and upcoming:
        upcoming_ids = [m.id for m in upcoming]
        preds = db.query(models.Prediction).filter(
            models.Prediction.user_id == user.id,
            models.Prediction.match_id.in_(upcoming_ids),
        ).all()
        for p in preds:
            if p.match_id not in user_predictions:
                user_predictions[p.match_id] = p

    # League used for predict links on the home page.
    # Admin can set a user's main_league_id; otherwise fall back to first membership.
    first_league_id = None
    if user and user.memberships:
        member_league_ids = {m.league_id for m in user.memberships}
        if user.main_league_id and user.main_league_id in member_league_ids:
            first_league_id = user.main_league_id
        else:
            first_league_id = user.memberships[0].league_id

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request, "user": user,
            "upcoming": upcoming, "user_leagues": user_leagues,
            "fav_ids": fav_ids,
            "has_favourites": has_favourites,
            "now": datetime.utcnow(),
            "first_match": first_match,
            "member_counts": counts,
            "user_predictions": user_predictions,
            "first_league_id": first_league_id,
        },
    )


@app.get("/rules")
async def rules_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    return templates.TemplateResponse("rules.html", {"request": request, "user": user})


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
