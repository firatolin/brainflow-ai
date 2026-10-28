from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditEvent(Base):
    """Append-only operational event log.

    Never UPDATE or DELETE via the app; only INSERT.
    """
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
