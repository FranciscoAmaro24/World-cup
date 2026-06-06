"""
Shared fixtures. Sets DATABASE_URL to in-memory SQLite BEFORE any app import
so the app never touches the real worldcup.db.
"""
import os
import sys

# Must be set before any app module is imported
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "test-secret-not-for-production-xyz")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest                                      # noqa: E402
from fastapi.testclient import TestClient           # noqa: E402
from sqlalchemy.orm import sessionmaker            # noqa: E402

import database                                    # noqa: E402
from database import Base, get_db, engine          # noqa: E402
from main import app                               # noqa: E402

TestSession = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(client, username="testuser", password="password123"):
    client.post("/register", data={
        "username": username,
        "email": f"{username}@test.com",
        "password": password,
        "confirm_password": password,
    }, follow_redirects=True)
    resp = client.post("/login", data={"username": username, "password": password},
                       follow_redirects=True)
    assert resp.status_code == 200
    return client
