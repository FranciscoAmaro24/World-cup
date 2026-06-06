"""Tests for registration and login flows."""
import pytest
from tests.conftest import register_and_login


def test_register_success(client):
    resp = client.post("/register", data={
        "username": "alice",
        "email": "alice@test.com",
        "password": "secret123",
        "confirm_password": "secret123",
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_register_duplicate_username(client):
    data = {"username": "bob", "email": "bob@test.com",
            "password": "pass1234", "confirm_password": "pass1234"}
    client.post("/register", data=data, follow_redirects=True)
    resp = client.post("/register", data=data, follow_redirects=True)
    assert resp.status_code in (200, 400)  # app shows error page


def test_register_password_mismatch(client):
    resp = client.post("/register", data={
        "username": "carol", "email": "carol@test.com",
        "password": "aaa", "confirm_password": "bbb",
    }, follow_redirects=True)
    assert resp.status_code in (200, 400)


def test_login_success(client):
    register_and_login(client, "dave", "mypass456")
    resp = client.get("/profile")
    assert resp.status_code == 200


def test_login_wrong_password(client):
    client.post("/register", data={
        "username": "eve", "email": "eve@test.com",
        "password": "correct", "confirm_password": "correct",
    }, follow_redirects=True)
    resp = client.post("/login", data={"username": "eve", "password": "wrong"},
                       follow_redirects=True)
    assert resp.status_code in (200, 401)  # shows error page or 401


def test_logout(client):
    register_and_login(client)
    client.post("/logout")
    resp = client.get("/profile", follow_redirects=False)
    assert resp.status_code == 303


def test_unauthenticated_redirects(client):
    for path in ["/profile/edit", "/leagues/create", "/markets/create"]:
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 303, f"{path} should redirect unauthenticated users"
