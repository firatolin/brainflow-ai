"""TEMPORARY diagnostic endpoint. Remove before public exposure."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models import User


router = APIRouter(prefix="/_diag", tags=["diag"], include_in_schema=False)


@router.get("")
def diag(db: Session = Depends(get_db)):
    db_url = settings.DATABASE_URL
    # Redact password from URL
    if "@" in db_url and "://" in db_url:
        scheme, rest = db_url.split("://", 1)
        if "@" in rest:
            creds, host = rest.split("@", 1)
            if ":" in creds:
                user, _ = creds.split(":", 1)
                redacted = f"{scheme}://{user}:***@{host}"
            else:
                redacted = db_url
        else:
            redacted = db_url
    else:
        redacted = db_url

    users = db.query(User).all()
    return {
        "db_url_redacted": redacted,
        "admin_username_setting": settings.ADMIN_USERNAME,
        "admin_password_length": len(settings.ADMIN_PASSWORD),
        "admin_password_is_default": settings.ADMIN_PASSWORD == "BrainFlow@2026",
        "users_total": len(users),
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "display_name": u.display_name,
                "active": u.active,
                "password_hash_prefix": u.password_hash[:20] if u.password_hash else None,
            }
            for u in users
        ],
    }
