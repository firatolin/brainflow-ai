from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.integrations.llm_client import get_llm_provider


router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db_ok = True
    db_error = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        db_error = str(exc)

    provider = get_llm_provider()

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "database": {"ok": db_ok, "error": db_error},
        "ai": {
            "provider": provider.name,
            "configured": provider.available,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
