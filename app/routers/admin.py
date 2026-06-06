import asyncio
from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session
import os

BG_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "bg_video.mp4")

from database import get_db
import models
import auth
from shared import templates
from routers.predictions import calculate_points
from services import results_fetcher

router = APIRouter(prefix="/admin")

ROUND_LABELS = {
    "group": "Group Stage", "r32": "Round of 32", "r16": "Round of 16",
    "qf": "Quarter-final", "sf": "Semi-final", "third": "Third Place", "final": "Final",
}


def _require_admin(request: Request, db: Session):
    user = auth.get_current_user(request, db)
    if not user or not user.is_superadmin:
        return None
    return user


@router.get("")
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    group_matches = (
        db.query(models.Match).filter(models.Match.round == "group")
        .order_by(models.Match.match_date).all()
    )
    knockout_matches = (
        db.query(models.Match).filter(models.Match.round != "group")
        .order_by(models.Match.match_date).all()
    )
    all_teams = db.query(models.Team).order_by(models.Team.group_letter, models.Team.name).all()
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": user,
            "group_matches": group_matches,
            "knockout_matches": knockout_matches,
            "all_teams": all_teams,
            "round_labels": ROUND_LABELS,
            "last_fetch": results_fetcher.last_fetch,
            "last_error": results_fetcher.last_error,
            "bg_video_exists": os.path.exists(BG_VIDEO_PATH),
        },
    )


@router.post("/matches/{match_id}")
async def update_result(
    request: Request,
    match_id: int,
    home_score: int = Form(...),
    away_score: int = Form(...),
    winner_team_id: int = Form(0),
    home_scorers: str = Form(""),
    away_scorers: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not match:
        return RedirectResponse("/admin", status_code=303)

    match.home_score = home_score
    match.away_score = away_score
    match.status = "finished"

    # For knockout matches, record the advancing team
    if match.is_knockout():
        if winner_team_id and winner_team_id > 0:
            match.winner_team_id = winner_team_id
        elif home_score > away_score:
            match.winner_team_id = match.home_team_id
        elif away_score > home_score:
            match.winner_team_id = match.away_team_id
        # Update eliminated / stage_reached
        if match.winner_team_id:
            loser_id = (
                match.away_team_id if match.winner_team_id == match.home_team_id else match.home_team_id
            )
            _set_stage(db, match.winner_team_id, match.round, winner=(match.round == "final"))
            if loser_id:
                loser = db.query(models.Team).filter(models.Team.id == loser_id).first()
                if loser:
                    loser.eliminated = True

    # Parse and store goal scorers (manual entry)
    if home_scorers.strip() or away_scorers.strip():
        db.query(models.Goal).filter(models.Goal.match_id == match_id).delete()
        for raw, team_id in [(home_scorers, match.home_team_id), (away_scorers, match.away_team_id)]:
            for line in raw.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                is_og = "(og)" in line.lower()
                is_pen = "(pen)" in line.lower()
                name_part = line.replace("(og)", "").replace("(pen)", "").strip()
                minute = None
                # Parse "Name 45" or "Name 45'" formats
                parts = name_part.rsplit(" ", 1)
                if len(parts) == 2:
                    min_str = parts[1].replace("'", "").replace("+", "")
                    try:
                        minute = int(min_str)
                        name_part = parts[0]
                    except ValueError:
                        pass
                db.add(models.Goal(
                    match_id=match_id,
                    team_id=team_id,
                    player_name=name_part.strip(),
                    minute=minute,
                    is_own_goal=is_og,
                    is_penalty=is_pen,
                ))

    # Recalculate match prediction points for all leagues
    for pred in match.predictions:
        league = db.query(models.League).filter(models.League.id == pred.league_id).first()
        if league:
            pred.points_awarded = calculate_points(pred, match, league)

    # Recalculate bracket points if we just finished an SF or the Final
    if match.is_knockout() and match.round in ("sf", "final"):
        from bracket_utils import get_actual_bracket, calc_bracket_points
        actual = get_actual_bracket(db)
        db.flush()
        actual = get_actual_bracket(db)
        for league in db.query(models.League).all():
            for pick in db.query(models.TournamentPick).filter(
                models.TournamentPick.league_id == league.id
            ).all():
                pick.points_awarded = calc_bracket_points(pick, league, actual)

    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/matches/{match_id}/reset")
async def reset_result(request: Request, match_id: int, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not match:
        return RedirectResponse("/admin", status_code=303)
    match.home_score = None
    match.away_score = None
    match.winner_team_id = None
    match.status = "scheduled"
    for pred in match.predictions:
        pred.points_awarded = None
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/matches/create")
async def create_knockout_match(
    request: Request,
    round: str = Form(...),
    match_date: str = Form(...),
    venue: str = Form(...),
    home_team_id: int = Form(0),
    away_team_id: int = Form(0),
    home_team_tbd: str = Form(""),
    away_team_tbd: str = Form(""),
    db: Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    try:
        dt = datetime.strptime(match_date, "%Y-%m-%dT%H:%M")
    except ValueError:
        dt = datetime.strptime(match_date, "%Y-%m-%d %H:%M")

    max_num = db.query(models.Match.match_number).order_by(models.Match.match_number.desc()).first()
    next_num = (max_num[0] + 1) if max_num else 100

    match = models.Match(
        match_number=next_num,
        home_team_id=home_team_id if home_team_id > 0 else None,
        away_team_id=away_team_id if away_team_id > 0 else None,
        home_team_tbd=home_team_tbd.strip() or None,
        away_team_tbd=away_team_tbd.strip() or None,
        round=round,
        match_date=dt,
        venue=venue.strip(),
    )
    db.add(match)
    db.commit()
    return RedirectResponse("/admin#knockout", status_code=303)


@router.post("/matches/{match_id}/delete")
async def delete_match(request: Request, match_id: int, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if match and match.is_knockout():
        db.delete(match)
        db.commit()
    return RedirectResponse("/admin#knockout", status_code=303)


@router.post("/fetch")
async def manual_fetch(request: Request, db: Session = Depends(get_db)):
    """Trigger an immediate auto-fetch of results."""
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    asyncio.create_task(results_fetcher.fetch_now(db))
    return RedirectResponse("/admin", status_code=303)


@router.post("/video/upload")
async def upload_bg_video(
    request: Request,
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    if not (video.filename or "").lower().endswith(".mp4"):
        return RedirectResponse("/admin?err=not_mp4", status_code=303)
    os.makedirs(os.path.dirname(BG_VIDEO_PATH), exist_ok=True)
    with open(BG_VIDEO_PATH, "wb") as f:
        while chunk := await video.read(1024 * 1024):  # 1 MB chunks
            f.write(chunk)
    return RedirectResponse("/admin?msg=video_uploaded", status_code=303)


@router.post("/video/remove")
async def remove_bg_video(request: Request, db: Session = Depends(get_db)):
    user = _require_admin(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    try:
        os.remove(BG_VIDEO_PATH)
    except OSError:
        pass
    return RedirectResponse("/admin?msg=video_removed", status_code=303)


def _set_stage(db, team_id: int, round_code: str, winner: bool = False):
    from services.results_fetcher import STAGE_REACHED
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        return
    new_stage = "winner" if winner else round_code
    if STAGE_REACHED.get(new_stage, 0) > STAGE_REACHED.get(team.stage_reached or "group", 0):
        team.stage_reached = new_stage
