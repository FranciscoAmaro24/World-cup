from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session
from datetime import datetime
import os

from database import get_db
import models
import auth
from shared import templates

router = APIRouter()

ROUND_ORDER = {"group": 0, "r32": 1, "r16": 2, "qf": 3, "sf": 4, "third": 5, "final": 6}
ROUND_LABELS = {
    "group": "Group Stage",
    "r32": "Round of 32",
    "r16": "Round of 16",
    "qf": "Quarter-finals",
    "sf": "Semi-finals",
    "third": "Third Place",
    "final": "Final",
}


ROUND_SIZES = {"r32": 16, "r16": 8, "qf": 4, "sf": 2, "final": 1}

# 2026 WC knockout schedule (UTC). Teams TBD until group stage finishes.
KO_SCHEDULE = [
    # (match_number, round, date_utc, venue)
    (73,  "r32", "2026-06-28 21:00", "MetLife Stadium, East Rutherford"),
    (74,  "r32", "2026-06-29 01:00", "SoFi Stadium, Inglewood"),
    (75,  "r32", "2026-06-29 21:00", "AT&T Stadium, Arlington"),
    (76,  "r32", "2026-06-30 01:00", "Mercedes-Benz Stadium, Atlanta"),
    (77,  "r32", "2026-06-30 21:00", "Estadio Azteca, Mexico City"),
    (78,  "r32", "2026-07-01 01:00", "NRG Stadium, Houston"),
    (79,  "r32", "2026-07-01 21:00", "Lumen Field, Seattle"),
    (80,  "r32", "2026-07-02 01:00", "BC Place, Vancouver"),
    (81,  "r32", "2026-07-02 21:00", "Hard Rock Stadium, Miami Gardens"),
    (82,  "r32", "2026-07-03 01:00", "Lincoln Financial Field, Philadelphia"),
    (83,  "r32", "2026-07-03 21:00", "Gillette Stadium, Foxborough"),
    (84,  "r32", "2026-07-04 01:00", "Arrowhead Stadium, Kansas City"),
    (85,  "r32", "2026-07-04 21:00", "Levi's Stadium, Santa Clara"),
    (86,  "r32", "2026-07-04 23:00", "Estadio BBVA, Monterrey"),
    (87,  "r32", "2026-07-05 02:00", "Estadio Akron, Zapopan"),
    (88,  "r32", "2026-07-05 22:00", "BMO Field, Toronto"),
    (89,  "r16", "2026-07-07 19:00", "MetLife Stadium, East Rutherford"),
    (90,  "r16", "2026-07-07 23:00", "AT&T Stadium, Arlington"),
    (91,  "r16", "2026-07-08 19:00", "SoFi Stadium, Inglewood"),
    (92,  "r16", "2026-07-08 23:00", "Mercedes-Benz Stadium, Atlanta"),
    (93,  "r16", "2026-07-09 19:00", "NRG Stadium, Houston"),
    (94,  "r16", "2026-07-09 23:00", "Lumen Field, Seattle"),
    (95,  "r16", "2026-07-10 02:00", "Hard Rock Stadium, Miami Gardens"),
    (96,  "r16", "2026-07-10 22:00", "Estadio Azteca, Mexico City"),
    (97,  "qf",  "2026-07-12 19:00", "MetLife Stadium, East Rutherford"),
    (98,  "qf",  "2026-07-12 23:00", "AT&T Stadium, Arlington"),
    (99,  "qf",  "2026-07-13 19:00", "SoFi Stadium, Inglewood"),
    (100, "qf",  "2026-07-13 23:00", "Mercedes-Benz Stadium, Atlanta"),
    (101, "sf",  "2026-07-15 22:00", "MetLife Stadium, East Rutherford"),
    (102, "sf",  "2026-07-16 22:00", "AT&T Stadium, Arlington"),
    (103, "third","2026-07-18 19:00","SoFi Stadium, Inglewood"),
    (104, "final","2026-07-19 22:00", "MetLife Stadium, East Rutherford"),
]


def _ensure_ko_schedule(db: Session):
    """Insert KO schedule rows if not already present."""
    from datetime import datetime as dt
    for num, rnd, date_str, venue in KO_SCHEDULE:
        exists = db.query(models.Match).filter(models.Match.match_number == num).first()
        if not exists:
            db.add(models.Match(
                match_number=num,
                round=rnd,
                match_date=dt.strptime(date_str, "%Y-%m-%d %H:%M"),
                venue=venue,
            ))
    db.commit()


@router.get("/knockout")
async def knockout_bracket(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    _ensure_ko_schedule(db)

    ko_matches = (
        db.query(models.Match)
        .filter(models.Match.round.in_(["r32", "r16", "qf", "sf", "final"]))
        .order_by(models.Match.match_number)
        .all()
    )

    rounds: dict[str, list] = {r: [] for r in ["r32", "r16", "qf", "sf", "final"]}
    for m in ko_matches:
        if m.round in rounds:
            rounds[m.round].append(m)

    # Pad each round to expected count with None slots
    for rnd, expected in ROUND_SIZES.items():
        while len(rounds[rnd]) < expected:
            rounds[rnd].append(None)

    # Build paired structure: list of (match_a, match_b) for each round
    # Final has just one match
    def to_pairs(lst):
        pairs = []
        for i in range(0, len(lst), 2):
            pairs.append((lst[i], lst[i + 1] if i + 1 < len(lst) else None))
        return pairs

    bracket = {
        "r32":   to_pairs(rounds["r32"]),
        "r16":   to_pairs(rounds["r16"]),
        "qf":    to_pairs(rounds["qf"]),
        "sf":    to_pairs(rounds["sf"]),
        "final": rounds["final"][0] if rounds["final"] else None,
    }

    return templates.TemplateResponse(
        "matches/bracket.html",
        {
            "request": request,
            "user": user,
            "bracket": bracket,
            "now": datetime.utcnow(),
        },
    )


@router.get("/fixtures")
async def fixtures(request: Request, db: Session = Depends(get_db)):
    user = auth.get_current_user(request, db)
    all_matches = db.query(models.Match).order_by(models.Match.match_date).all()

    grouped = {}
    for m in all_matches:
        key = m.match_date.strftime("%Y-%m-%d")
        grouped.setdefault(key, []).append(m)

    return templates.TemplateResponse(
        "matches/list.html",
        {
            "request": request,
            "user": user,
            "grouped": grouped,
            "round_labels": ROUND_LABELS,
            "now": datetime.utcnow(),
        },
    )
