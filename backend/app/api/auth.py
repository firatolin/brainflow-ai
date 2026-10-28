from typing import Optional
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.auth import current_user_optional
from app.schemas.auth import AuthStatus, LoginRequest, UserRead
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=auth_service.SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.SESSION_TTL_HOURS * 3600,
        path="/",
    )


@router.post("/login", response_model=UserRead)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = auth_service.create_session(db, user)
    _set_cookie(response, token)
    return user


@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    session_cookie: Optional[str] = Cookie(default=None, alias=auth_service.SESSION_COOKIE),
):
    auth_service.revoke_session(db, session_cookie)
    response.delete_cookie(auth_service.SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/status", response_model=AuthStatus)
def status(user=Depends(current_user_optional)):
    if user is None:
        return AuthStatus(authenticated=False, user=None)
    return AuthStatus(authenticated=True, user=UserRead.model_validate(user))
