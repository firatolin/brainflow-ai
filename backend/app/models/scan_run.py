from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|ok|failed
    deliveries_scanned: Mapped[int] = mapped_column(Integer, default=0)
    incidents_created: Mapped[int] = mapped_column(Integer, default=0)
    incidents_reopened: Mapped[int] = mapped_column(Integer, default=0)
    incidents_auto_resolved: Mapped[int] = mapped_column(Integer, default=0)
    errors_json: Mapped[str] = mapped_column(Text, default="[]")
    triggered_by: Mapped[str] = mapped_column(String(20), default="manual")  # manual|scheduled
