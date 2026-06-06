"""Tests for the prediction markets feature."""
from datetime import datetime, timedelta
from tests.conftest import register_and_login


def _future():
    return (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")


def create_market(client, title="Will Spain win?", options=("Yes", "No")):
    data = {"title": title, "closes_at": _future()}
    for opt in options:
        data.setdefault("options[]", [])
        if isinstance(data["options[]"], list):
            data["options[]"].append(opt)
        else:
            data["options[]"] = [data["options[]"], opt]
    resp = client.post("/markets/create", data=data, follow_redirects=True)
    assert resp.status_code == 200
    return resp


def test_create_market(client):
    register_and_login(client)
    resp = create_market(client)
    assert b"Will Spain win?" in resp.content


def test_create_market_requires_login(client):
    resp = client.post("/markets/create", data={
        "title": "test", "closes_at": _future(), "options[]": ["A", "B"],
    }, follow_redirects=False)
    assert resp.status_code == 303


def test_create_market_needs_two_options(client):
    register_and_login(client)
    resp = client.post("/markets/create", data={
        "title": "bad", "closes_at": _future(), "options[]": ["Only one"],
    }, follow_redirects=True)
    assert resp.status_code in (200, 400)
    assert b"2" in resp.content or b"options" in resp.content.lower()


def test_place_bet(client, db):
    register_and_login(client)
    create_market(client)
    import models
    market = db.query(models.Market).first()
    option = market.options[0]
    resp = client.post(f"/markets/{market.id}/bet", data={
        "option_id": str(option.id), "amount": "2.0",
    }, follow_redirects=True)
    assert resp.status_code == 200
    db.expire_all()
    user = db.query(models.User).filter(models.User.username == "testuser").first()
    assert user.credits == 8.0


def test_bet_insufficient_credits(client, db):
    register_and_login(client)
    create_market(client)
    import models
    market = db.query(models.Market).first()
    option = market.options[0]
    resp = client.post(f"/markets/{market.id}/bet", data={
        "option_id": str(option.id), "amount": "999",
    }, follow_redirects=True)
    assert resp.status_code == 200
    db.expire_all()
    user = db.query(models.User).filter(models.User.username == "testuser").first()
    assert user.credits == 10.0  # unchanged


def test_resolve_market(client, db):
    register_and_login(client)
    create_market(client)
    import models
    market = db.query(models.Market).first()
    winning = market.options[0]
    resp = client.post(f"/markets/{market.id}/resolve", data={
        "winning_option_id": str(winning.id),
    }, follow_redirects=True)
    assert resp.status_code == 200
    db.expire_all()
    assert db.query(models.Market).first().resolved is True


def test_malformed_bet_option_id(client, db):
    """option_id must be handled gracefully even if not an integer."""
    register_and_login(client)
    create_market(client)
    import models
    market = db.query(models.Market).first()
    resp = client.post(f"/markets/{market.id}/bet", data={
        "option_id": "not-a-number", "amount": "1",
    }, follow_redirects=True)
    assert resp.status_code == 200  # should not 500
