from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Request
from sqlalchemy.orm import Session
import os
import models

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY == "CHANGE-THIS-TO-A-LONG-RANDOM-SECRET-IN-PRODUCTION":
    raise RuntimeError("SECRET_KEY env var is not set. Run: export SECRET_KEY=$(openssl rand -hex 32)")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


RESET_EXPIRE_HOURS = 24


def create_reset_token(user: "models.User") -> str:
    """One-time-ish password reset token. Signed with the user's current password hash so it
    becomes invalid as soon as the password changes (single use) and expires after 24h."""
    expire = datetime.utcnow() + timedelta(hours=RESET_EXPIRE_HOURS)
    key = SECRET_KEY + user.password_hash
    return jwt.encode({"sub": str(user.id), "purpose": "reset", "exp": expire}, key, algorithm=ALGORITHM)


def verify_reset_token(token: str, db: Session) -> Optional["models.User"]:
    try:
        claims = jwt.get_unverified_claims(token)
        if claims.get("purpose") != "reset":
            return None
        user = db.query(models.User).filter(models.User.id == int(claims.get("sub", 0))).first()
        if not user:
            return None
        # Re-verify signature + expiry with the password-bound key
        jwt.decode(token, SECRET_KEY + user.password_hash, algorithms=[ALGORITHM])
        return user
    except (JWTError, ValueError):
        return None


def get_current_user(request: Request, db: Session) -> Optional[models.User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        return None
    return db.query(models.User).filter(models.User.id == user_id).first()
