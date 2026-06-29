from datetime import datetime
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session
import os

from database import get_db
import models
import auth
from shared import templates

router = APIRouter()


# ── Scoring config caches (cleared when the admin edits round points / minute) ──
_round_points_cache: dict | None = None
_scoring_minute_cache: str | None = None
_DEFAULT_ROUND_POINTS = {"group": (2, 4), "r32": (2, 4), "r16": (3, 5),
                         "qf": (4, 6), "sf": (5, 7), "third": (5, 7), "final": (6, 8)}


def clear_scoring_cache():
    global _round_points_cache, _scoring_minute_cache
    _round_points_cache = None
    _scoring_minute_cache = None


def _round_points(db) -> dict:
    global _round_points_cache
    if _round_points_cache is None and db is not None:
        rows = db.query(models.RoundScoring).all()
        _round_points_cache = {r.round_code: (r.outcome_points, r.exact_points) for r in rows} or dict(_DEFAULT_ROUND_POINTS)
    return _round_points_cache or _DEFAULT_ROUND_POINTS


def _scoring_minute(db) -> str:
    global _scoring_minute_cache
    if _scoring_minute_cache is None and db is not None:
        s = db.query(models.AppSetting).filter_by(key="scoring_minute").first()
        _scoring_minute_cache = (s.value if s and s.value in ("90", "120") else "120")
    return _scoring_minute_cache or "120"


def _scores_for(match, minute: str):
    """Return (home, away) to score against, honouring the 90-vs-120 minute rule."""
    if minute == "90" and match.home_score_reg is not None and match.away_score_reg is not None:
        return match.home_score_reg, match.away_score_reg
    return match.home_score, match.away_score


def calculate_points(pred: models.Prediction, match: models.Match, league: models.League = None) -> int:
    if match.home_score is None or match.away_score is None:
        return 0
    db = Session.object_session(pred) or Session.object_session(match)
    minute = _scoring_minute(db)
    home_actual, away_actual = _scores_for(match, minute)
    if home_actual is None or away_actual is None:
        return 0

    outcome_pts, exact_pts = _round_points(db).get(match.round, _DEFAULT_ROUND_POINTS["group"])

    if pred.home_score_pred == home_actual and pred.away_score_pred == away_actual:
        return exact_pts
    if _result(pred.home_score_pred, pred.away_score_pred) == _result(home_actual, away_actual):
        return outcome_pts
    return 0


def _result(h, a):
    if h > a:
        return "H"
    if h < a:
        return "A"
    return "D"


@router.get("/leagues/{league_id}/predict/{match_id}")
async def predict_page(request: Request, league_id: int, match_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not league or not match:
        return RedirectResponse(f"/leagues/{league_id}", status_code=303)
    membership = db.query(models.LeagueMember).filter(
        models.LeagueMember.league_id == league_id,
        models.LeagueMember.user_id == user.id,
    ).first()
    if not membership:
        return RedirectResponse("/leagues", status_code=303)
    if match.is_locked():
        return RedirectResponse(f"/leagues/{league_id}", status_code=303)
    existing = db.query(models.Prediction).filter(
        models.Prediction.user_id == user.id,
        models.Prediction.match_id == match_id,
    ).first()
    outcome_pts, exact_pts = _round_points(db).get(match.round, _DEFAULT_ROUND_POINTS["group"])
    return templates.TemplateResponse(
        "predictions/predict.html",
        {
            "request": request,
            "user": user,
            "league": league,
            "match": match,
            "prediction": existing,
            "exact_pts": exact_pts,
            "result_pts": outcome_pts,
            "error": None,
        },
    )


@router.post("/leagues/{league_id}/predict/{match_id}")
async def save_prediction(
    request: Request,
    league_id: int,
    match_id: int,
    home_score: int = Form(...),
    away_score: int = Form(...),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    league = db.query(models.League).filter(models.League.id == league_id).first()
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not league or not match:
        return RedirectResponse(f"/leagues/{league_id}", status_code=303)
    membership = db.query(models.LeagueMember).filter(
        models.LeagueMember.league_id == league_id,
        models.LeagueMember.user_id == user.id,
    ).first()
    if not membership or match.is_locked():
        return RedirectResponse(f"/leagues/{league_id}", status_code=303)
    if home_score < 0 or away_score < 0 or home_score > 20 or away_score > 20:
        return RedirectResponse(f"/leagues/{league_id}", status_code=303)
    now = datetime.utcnow()

    # All leagues the user belongs to
    all_league_ids = [
        m.league_id for m in db.query(models.LeagueMember).filter(
            models.LeagueMember.user_id == user.id
        ).all()
    ]

    # Upsert a prediction row for every league the user is in
    for lid in all_league_ids:
        pred = db.query(models.Prediction).filter(
            models.Prediction.user_id == user.id,
            models.Prediction.match_id == match_id,
            models.Prediction.league_id == lid,
        ).first()
        if pred:
            pred.home_score_pred = home_score
            pred.away_score_pred = away_score
            pred.submitted_at = now
        else:
            db.add(models.Prediction(
                user_id=user.id,
                match_id=match_id,
                league_id=lid,
                home_score_pred=home_score,
                away_score_pred=away_score,
            ))

    db.commit()
    return RedirectResponse(f"/leagues/{league_id}", status_code=303)
