"""Tests for image upload validation (type, size limits)."""
import io
from tests.conftest import register_and_login


def _fake_image(ext=".jpg", size=1000):
    """Return a minimal fake image payload."""
    # Minimal valid JPEG header bytes so Pillow can open it
    # For tests we bypass Pillow by mocking; here we just test the route logic
    return io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * size)


def test_avatar_upload_wrong_type(client):
    register_and_login(client)
    resp = client.post("/profile/avatar", files={
        "avatar": ("photo.exe", io.BytesIO(b"bad"), "application/octet-stream"),
    }, follow_redirects=True)
    assert resp.status_code in (200, 400)
    assert b"JPG" in resp.content or b"PNG" in resp.content or b"Image" in resp.content


def test_avatar_upload_too_large(client):
    register_and_login(client)
    big = io.BytesIO(b"\xff\xd8\xff\xe0" + b"x" * (11 * 1024 * 1024))
    resp = client.post("/profile/avatar", files={
        "avatar": ("photo.jpg", big, "image/jpeg"),
    }, follow_redirects=True)
    assert resp.status_code in (200, 400)
    assert b"10" in resp.content  # "max 10 MB" message


def test_market_image_upload_wrong_type(client):
    from datetime import datetime, timedelta
    register_and_login(client)
    # Create market via HTTP so session is consistent
    closes = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    client.post("/markets/create", data={
        "title": "img test", "closes_at": closes,
        "options[]": ["Yes", "No"],
    }, follow_redirects=True)
    # Try uploading a non-image file — should not crash
    resp = client.post("/markets/1/image", files={
        "image": ("vid.mp4", io.BytesIO(b"data"), "video/mp4"),
    }, follow_redirects=False)
    assert resp.status_code in (200, 303)
