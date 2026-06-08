"""Tests for the prediction flow: submit, update, boost, scoring."""
from datetime import datetime, timedelta
import models
from tests.conftest import register_and_login


# ── helpers ───────────────────────────────────────────────────

def _future_match(db) -> tuple[int, int]:
    """Insert a schedulable match + league; return (match_id, league_id)."""
    user_id = db.query(models.User).first().id

    match = models.Match(
        match_number=9001, round="group",
        match_date=datetime.utcnow() + timedelta(hours=2),
        venue="Test Stadium", status="scheduled", group_letter="A",
    )
    db.add(match)
    db.flush()
    match_id = match.id

    league = models.League(
        name="Test League", invite_code="TSTLG1",
        admin_id=user_id, points_exact_score=5, points_correct_result=2,
    )
    db.add(league)
    db.flush()
    league_id = league.id

    db.add(models.LeagueMember(league_id=league_id, user_id=user_id))
    db.commit()
    return match_id, league_id


def _locked_match(db, league_id: int) -> int:
    """Insert a finished (locked) match; return match_id."""
    match = models.Match(
        match_number=9002, round="group",
        match_date=datetime.utcnow() - timedelta(hours=2),
        venue="Past Stadium", status="finished",
        home_score=2, away_score=1, group_letter="B",
    )
    db.add(match)
    db.commit()
    return match.id


# ── prediction submit ─────────────────────────────────────────

def test_submit_prediction(client, db):
    register_and_login(client)
    match_id, league_id = _future_match(db)

    resp = client.post(
        f"/leagues/{league_id}/predict/{match_id}",
        data={"home_score": "2", "away_score": "1", "boosted": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    db.expire_all()
    pred = db.query(models.Prediction).filter_by(match_id=match_id).first()
    assert pred is not None
    assert pred.home_score_pred == 2
    assert pred.away_score_pred == 1
    assert pred.boosted is False


def test_submit_prediction_with_boost(client, db):
    register_and_login(client)
    match_id, league_id = _future_match(db)

    client.post(
        f"/leagues/{league_id}/predict/{match_id}",
        data={"home_score": "3", "away_score": "0", "boosted": "1"},
        follow_redirects=True,
    )
    db.expire_all()
    pred = db.query(models.Prediction).filter_by(match_id=match_id).first()
    assert pred is not None
    assert pred.boosted is True


def test_update_prediction_no_duplicate(client, db):
    register_and_login(client)
    match_id, league_id = _future_match(db)

    for score in [("1", "0"), ("2", "2")]:
        client.post(
            f"/leagues/{league_id}/predict/{match_id}",
            data={"home_score": score[0], "away_score": score[1], "boosted": ""},
            follow_redirects=True,
        )
    db.expire_all()
    preds = db.query(models.Prediction).filter_by(match_id=match_id).all()
    assert len(preds) == 1
    assert preds[0].home_score_pred == 2
    assert preds[0].away_score_pred == 2


def test_predict_rejects_locked_match(client, db):
    register_and_login(client)
    match_id, league_id = _future_match(db)
    locked_id = _locked_match(db, league_id)

    resp = client.post(
        f"/leagues/{league_id}/predict/{locked_id}",
        data={"home_score": "1", "away_score": "0"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    db.expire_all()
    assert db.query(models.Prediction).filter_by(match_id=locked_id).first() is None


def test_predict_page_renders(client, db):
    register_and_login(client)
    match_id, league_id = _future_match(db)
    resp = client.get(f"/leagues/{league_id}/predict/{match_id}")
    assert resp.status_code == 200
    assert b"step-up" in resp.content
    assert b"step-down" in resp.content
    assert b"Boost" in resp.content
    assert b"DOMContentLoaded" in resp.content


def test_predict_requires_login(client, db):
    register_and_login(client)
    match_id, league_id = _future_match(db)
    client.post("/logout")

    resp = client.get(
        f"/leagues/{league_id}/predict/{match_id}",
        follow_redirects=False,
    )
    assert resp.status_code == 303


# ── scoring logic (pure unit tests, no DB) ───────────────────

from routers.predictions import calculate_points  # noqa: E402


class _L:
    points_exact_score = 5
    points_correct_result = 2


def _pred(h, a, boosted=False):
    class P:
        home_score_pred = h
        away_score_pred = a
    P.boosted = boosted
    return P()


def _match(h, a):
    class M:
        home_score = h
        away_score = a
    return M()


def test_scoring_exact_no_boost():
    assert calculate_points(_pred(2, 1), _match(2, 1), _L()) == 5


def test_scoring_exact_with_boost():
    assert calculate_points(_pred(2, 1, boosted=True), _match(2, 1), _L()) == 10


def test_scoring_boost_miss_gives_zero():
    # correct result but not exact score → boosted = 0
    assert calculate_points(_pred(2, 1, boosted=True), _match(3, 1), _L()) == 0


def test_scoring_correct_result_no_boost():
    assert calculate_points(_pred(2, 1), _match(3, 1), _L()) == 2


def test_scoring_wrong_result():
    assert calculate_points(_pred(2, 1), _match(0, 2), _L()) == 0


def test_scoring_draw_exact():
    assert calculate_points(_pred(1, 1), _match(1, 1), _L()) == 5


def test_scoring_unfinished_match():
    class MUnfinished:
        home_score = None
        away_score = None
    assert calculate_points(_pred(1, 0), MUnfinished(), _L()) == 0
