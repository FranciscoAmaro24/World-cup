"""
Prediction Market — multi-option pari-mutuel markets.
Everyone starts with 10 credits. Create any question with 2-8 options.
Payouts: winners share the total pot proportionally to their stake.
"""
import os
import uuid
import json
from datetime import datetime
from typing import List
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
import models
import auth
from shared import templates
from image_utils import process_image

router = APIRouter(prefix="/markets")

MIN_BET = 0.1
MARKET_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "markets")
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE = 10 * 1024 * 1024


def _prob_history(market: models.Market, db: Session) -> str:
    """Return JSON for Chart.js: probability of each option over time as bets were placed."""
    bets = (
        db.query(models.Bet)
        .filter(models.Bet.market_id == market.id)
        .order_by(models.Bet.placed_at)
        .all()
    )
    if not bets:
        return "null"

    opts = {o.id: o.label for o in market.options}
    n = len(opts)
    if n == 0:
        return "null"

    # Track running totals per option
    totals = {oid: 0.0 for oid in opts}
    labels = []
    series = {oid: [] for oid in opts}

    def snapshot():
        pool = sum(totals.values())
        for oid in opts:
            prob = round(totals[oid] / pool * 100, 1) if pool > 0 else round(100.0 / n, 1)
            series[oid].append(prob)

    # Initial point (equal probability)
    labels.append("Start")
    snapshot()

    for bet in bets:
        totals[bet.option_id] = round(totals.get(bet.option_id, 0) + bet.amount, 4)
        labels.append(bet.placed_at.strftime("%d %b %H:%M"))
        snapshot()

    # Build Chart.js datasets
    COLORS = ["#4a9eff", "#f87171", "#4ade80", "#fbbf24", "#a78bfa", "#fb923c", "#34d399", "#f472b6"]
    datasets = []
    for i, (oid, label) in enumerate(opts.items()):
        datasets.append({
            "label": label,
            "data": series[oid],
            "borderColor": COLORS[i % len(COLORS)],
            "backgroundColor": COLORS[i % len(COLORS)] + "22",
            "borderWidth": 2,
            "pointRadius": 3,
            "pointHoverRadius": 5,
            "tension": 0.3,
            "fill": False,
        })

    return json.dumps({"labels": labels, "datasets": datasets})


def _payout_rate(market: models.Market, option: models.MarketOption) -> float:
    """Credits returned per credit bet on this option if it wins."""
    total = market.total_volume()
    if option.total_credits == 0:
        return 1.0
    return round(total / option.total_credits, 2)


def _resolve(market: models.Market, winning_option_id: int, db: Session):
    winning_opt = next((o for o in market.options if o.id == winning_option_id), None)
    if not winning_opt:
        return
    market.resolved = True
    market.winning_option_id = winning_option_id
    total_pool = market.total_volume()
    winning_pool = winning_opt.total_credits

    for bet in market.bets:
        if bet.option_id == winning_option_id:
            if winning_pool > 0:
                payout = (bet.amount / winning_pool) * total_pool
            else:
                payout = bet.amount
            bet.payout = round(payout, 4)
            user = db.query(models.User).filter(models.User.id == bet.user_id).first()
            if user:
                user.credits = round(user.credits + payout, 4)
        else:
            bet.payout = 0.0

    if winning_pool == 0:
        for bet in market.bets:
            user = db.query(models.User).filter(models.User.id == bet.user_id).first()
            if user:
                user.credits = round(user.credits + bet.amount, 4)
            bet.payout = bet.amount


@router.get("")
async def market_list(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    now = datetime.utcnow()
    open_markets = (
        db.query(models.Market)
        .filter(models.Market.resolved == False, models.Market.closes_at > now)
        .order_by(models.Market.created_at.desc())
        .all()
    )
    closed_markets = (
        db.query(models.Market)
        .filter(
            (models.Market.resolved == True) | (models.Market.closes_at <= now)
        )
        .order_by(models.Market.created_at.desc())
        .limit(20)
        .all()
    )
    user_bets: dict[int, models.Bet] = {}
    if user:
        for bet in db.query(models.Bet).filter(models.Bet.user_id == user.id).all():
            user_bets[bet.market_id] = bet
    return templates.TemplateResponse(
        "markets/list.html",
        {
            "request": request, "user": user,
            "open_markets": open_markets,
            "closed_markets": closed_markets,
            "user_bets": user_bets,
            "now": now,
        },
    )


@router.get("/create")
async def create_page(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        "markets/create.html", {"request": request, "user": user, "error": None}
    )


@router.post("/create")
async def create_market(
    request: Request,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    title = (form.get("title") or "").strip()[:200]
    description = (form.get("description") or "").strip()[:500] or None
    closes_at_str = form.get("closes_at", "")
    options_raw: List[str] = [
        v.strip() for k, v in form.multi_items() if k == "options[]" and v.strip()
    ]

    def err(msg):
        return templates.TemplateResponse(
            "markets/create.html",
            {"request": request, "user": user, "error": msg},
            status_code=400,
        )

    if not title:
        return err("Title is required")
    if len(options_raw) < 2:
        return err("At least 2 options are required")
    if len(options_raw) > 8:
        return err("Maximum 8 options allowed")
    if len(set(o.lower() for o in options_raw)) != len(options_raw):
        return err("Options must be unique")
    try:
        close_dt = datetime.strptime(closes_at_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        return err("Invalid close date")
    if close_dt <= datetime.utcnow():
        return err("Close date must be in the future")

    market = models.Market(
        creator_id=user.id,
        title=title,
        description=description,
        closes_at=close_dt,
    )
    db.add(market)
    db.flush()
    for label in options_raw:
        db.add(models.MarketOption(market_id=market.id, label=label[:100]))
    db.commit()
    db.refresh(market)
    return RedirectResponse(f"/markets/{market.id}", status_code=303)


@router.get("/{market_id}")
async def market_detail(request: Request, market_id: int, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not market:
        return RedirectResponse("/markets", status_code=303)

    user_bet = None
    if user:
        user_bet = (
            db.query(models.Bet)
            .filter(models.Bet.market_id == market_id, models.Bet.user_id == user.id)
            .first()
        )
    recent_bets = (
        db.query(models.Bet)
        .filter(models.Bet.market_id == market_id)
        .order_by(models.Bet.placed_at.desc())
        .limit(20)
        .all()
    )
    can_resolve = user and (user.id == market.creator_id or user.is_superadmin)
    payout_rates = {opt.id: _payout_rate(market, opt) for opt in market.options}
    winning_option = next(
        (o for o in market.options if o.id == market.winning_option_id), None
    ) if market.resolved else None
    chart_data = _prob_history(market, db)

    return templates.TemplateResponse(
        "markets/detail.html",
        {
            "request": request, "user": user,
            "market": market,
            "user_bet": user_bet,
            "recent_bets": recent_bets,
            "can_resolve": can_resolve,
            "payout_rates": payout_rates,
            "winning_option": winning_option,
            "chart_data": chart_data,
            "now": datetime.utcnow(),
        },
    )


@router.post("/{market_id}/image")
async def upload_market_image(
    request: Request,
    market_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not market or (user.id != market.creator_id and not user.is_superadmin):
        return RedirectResponse(f"/markets/{market_id}", status_code=303)

    ext = os.path.splitext(image.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        return RedirectResponse(f"/markets/{market_id}?err=filetype", status_code=303)
    data = await image.read()
    if len(data) > MAX_SIZE:
        return RedirectResponse(f"/markets/{market_id}?err=filesize", status_code=303)

    data, ext = process_image(data, "market")
    os.makedirs(MARKET_UPLOAD_DIR, exist_ok=True)
    filename = f"{market_id}_{uuid.uuid4().hex[:8]}{ext}"
    path = os.path.join(MARKET_UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(data)

    if market.img_url:
        old = os.path.join(os.path.dirname(__file__), "..", "static", market.img_url.lstrip("/"))
        try:
            os.remove(old)
        except OSError:
            pass

    market.img_url = f"/static/uploads/markets/{filename}"
    db.commit()
    return RedirectResponse(f"/markets/{market_id}", status_code=303)


@router.post("/{market_id}/bet")
async def place_bet(
    request: Request,
    market_id: int,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not market or not market.is_open():
        return RedirectResponse(f"/markets/{market_id}", status_code=303)

    form = await request.form()
    option_id = int(form.get("option_id", 0))
    try:
        amount = round(float(form.get("amount", 0)), 2)
    except (ValueError, TypeError):
        return RedirectResponse(f"/markets/{market_id}?err=invalid", status_code=303)

    option = next((o for o in market.options if o.id == option_id), None)
    if not option:
        return RedirectResponse(f"/markets/{market_id}?err=option", status_code=303)
    if amount < MIN_BET:
        return RedirectResponse(f"/markets/{market_id}?err=min", status_code=303)
    if user.credits < amount:
        return RedirectResponse(f"/markets/{market_id}?err=credits", status_code=303)

    existing = (
        db.query(models.Bet)
        .filter(models.Bet.market_id == market_id, models.Bet.user_id == user.id)
        .first()
    )
    if existing:
        user.credits = round(user.credits + existing.amount, 4)
        old_opt = next((o for o in market.options if o.id == existing.option_id), None)
        if old_opt:
            old_opt.total_credits = round(old_opt.total_credits - existing.amount, 4)
        db.delete(existing)
        db.flush()

    bet = models.Bet(
        market_id=market_id,
        user_id=user.id,
        option_id=option_id,
        amount=amount,
    )
    db.add(bet)
    user.credits = round(user.credits - amount, 4)
    option.total_credits = round(option.total_credits + amount, 4)
    db.commit()
    return RedirectResponse(f"/markets/{market_id}", status_code=303)


@router.post("/{market_id}/resolve")
async def resolve_market(
    request: Request,
    market_id: int,
    db: Session = Depends(get_db),
):
    user = auth.get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    market = db.query(models.Market).filter(models.Market.id == market_id).first()
    if not market or market.resolved:
        return RedirectResponse(f"/markets/{market_id}", status_code=303)
    if user.id != market.creator_id and not user.is_superadmin:
        return RedirectResponse(f"/markets/{market_id}", status_code=303)

    form = await request.form()
    winning_option_id = int(form.get("winning_option_id", 0))
    _resolve(market, winning_option_id, db)
    db.commit()
    return RedirectResponse(f"/markets/{market_id}", status_code=303)
