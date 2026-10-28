"""Password + session management for the single admin user."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import logging
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.session import SessionToken
from app.models.user import User


# Suppress passlib+bcrypt 4.x version-detection warning (harmless)
logging.getLogger('passlib').setLevel(logging.ERROR)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_COOKIE = settings.SESSION_COOKIE_NAME


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd.verify(plain, hashed)
    except Exception:
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ensure_admin_user(db: Session) -> User:
    """Idempotent: create the single admin from .env if not present."""
    existing = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
    if existing:
        # keep display name in sync with .env
        if existing.display_name != settings.ADMIN_DISPLAY_NAME:
            existing.display_name = settings.ADMIN_DISPLAY_NAME
            db.commit()
        return existing

    user = User(
        username=settings.ADMIN_USERNAME,
        display_name=settings.ADMIN_DISPLAY_NAME,
        password_hash=hash_password(settings.ADMIN_PASSWORD),
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username, User.active == True).first()  # noqa: E712
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: Session, user: User) -> str:
    """Returns the plaintext token (to set as cookie); only hash is stored."""
    raw = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_TTL_HOURS)
    db.add(SessionToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=expires,
    ))
    db.commit()
    return raw


def get_user_from_token(db: Session, raw_token: str | None) -> Optional[User]:
    if not raw_token:
        return None
    th = _hash_token(raw_token)
    row = db.query(SessionToken).filter(SessionToken.token_hash == th).first()
    if not row:
        return None
    if row.revoked_at is not None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return None
    return db.query(User).filter(User.id == row.user_id).first()


def revoke_session(db: Session, raw_token: str | None) -> None:
    if not raw_token:
        return
    th = _hash_token(raw_token)
    row = db.query(SessionToken).filter(SessionToken.token_hash == th).first()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
