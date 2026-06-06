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


def calculate_points(pred: models.Prediction, match: models.Match, league: models.League) -> int:
    if match.home_score is None or match.away_score is None:
        return 0
    if pred.home_score_pred == match.home_score and pred.away_score_pred == match.away_score:
        return league.points_exact_score
    pred_result = _result(pred.home_score_pred, pred.away_score_pred)
    actual_result = _result(match.home_score, match.away_score)
    if pred_result == actual_result:
        return league.points_correct_result
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
        models.Prediction.league_id == league_id,
    ).first()
    return templates.TemplateResponse(
        "predictions/predict.html",
        {
            "request": request,
            "user": user,
            "league": league,
            "match": match,
            "prediction": existing,
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
    existing = db.query(models.Prediction).filter(
        models.Prediction.user_id == user.id,
        models.Prediction.match_id == match_id,
        models.Prediction.league_id == league_id,
    ).first()
    if existing:
        existing.home_score_pred = home_score
        existing.away_score_pred = away_score
        existing.submitted_at = datetime.utcnow()
    else:
        pred = models.Prediction(
            user_id=user.id,
            match_id=match_id,
            league_id=league_id,
            home_score_pred=home_score,
            away_score_pred=away_score,
        )
        db.add(pred)
    db.commit()
    return RedirectResponse(f"/leagues/{league_id}", status_code=303)
