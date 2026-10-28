from typing import Optional
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services import auth_service


def current_user_optional(
    db: Session = Depends(get_db),
    session_cookie: Optional[str] = Cookie(default=None, alias=auth_service.SESSION_COOKIE),
) -> Optional[User]:
    return auth_service.get_user_from_token(db, session_cookie)


def require_user(
    db: Session = Depends(get_db),
    session_cookie: Optional[str] = Cookie(default=None, alias=auth_service.SESSION_COOKIE),
) -> User:
    user = auth_service.get_user_from_token(db, session_cookie)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Session"},
        )
    return user
