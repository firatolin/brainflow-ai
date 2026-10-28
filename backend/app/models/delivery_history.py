from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DeliveryHistory(Base):
    """Append-only history of status / assignment changes for a delivery."""

    __tablename__ = "delivery_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_id: Mapped[int] = mapped_column(
        ForeignKey("deliveries.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(60))  # created, updated, status_changed, assigned, unassigned
    from_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    from_vehicle_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    to_vehicle_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
