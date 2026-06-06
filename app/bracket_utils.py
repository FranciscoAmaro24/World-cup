"""Helpers for computing actual tournament bracket results from DB."""
from sqlalchemy.orm import Session
import models


def get_actual_bracket(db: Session) -> dict:
    """Returns teams that reached each knockout stage from finished match results."""
    result = {"winner": None, "finalists": set(), "semis": set(), "quarters": set()}

    final = (
        db.query(models.Match)
        .filter(models.Match.round == "final", models.Match.status == "finished")
        .first()
    )
    if final and final.winner_team_id:
        result["winner"] = final.winner_team_id
        if final.home_team_id:
            result["finalists"].add(final.home_team_id)
        if final.away_team_id:
            result["finalists"].add(final.away_team_id)

    for sf in db.query(models.Match).filter(models.Match.round == "sf", models.Match.status == "finished").all():
        if sf.home_team_id:
            result["semis"].add(sf.home_team_id)
        if sf.away_team_id:
            result["semis"].add(sf.away_team_id)

    for qf in db.query(models.Match).filter(models.Match.round == "qf", models.Match.status == "finished").all():
        if qf.home_team_id:
            result["quarters"].add(qf.home_team_id)
        if qf.away_team_id:
            result["quarters"].add(qf.away_team_id)

    return result


def calc_bracket_points(pick: models.TournamentPick, league: models.League, actual: dict) -> int:
    pts = 0
    if actual["winner"] and pick.winner_id == actual["winner"]:
        pts += league.points_bracket_winner
    if actual["finalists"] and pick.finalist_1_id in actual["finalists"]:
        pts += league.points_bracket_finalist
    if actual["semis"]:
        if pick.semi_1_id and pick.semi_1_id in actual["semis"]:
            pts += league.points_bracket_semi
        if pick.semi_2_id and pick.semi_2_id in actual["semis"]:
            pts += league.points_bracket_semi
    qpts = getattr(league, "points_bracket_quarter", 1)
    if actual["quarters"] and qpts:
        for attr in ["quarter_1_id", "quarter_2_id", "quarter_3_id", "quarter_4_id"]:
            tid = getattr(pick, attr, None)
            if tid and tid in actual["quarters"]:
                pts += qpts
    return pts


def is_bracket_locked(db: Session) -> bool:
    """Bracket picks lock when the first knockout match kicks off."""
    first_ko = (
        db.query(models.Match)
        .filter(models.Match.round != "group")
        .order_by(models.Match.match_date)
        .first()
    )
    if first_ko:
        from datetime import datetime
        return datetime.utcnow() >= first_ko.match_date
    return False
