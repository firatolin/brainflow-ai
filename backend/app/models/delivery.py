from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeliveryPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tracking_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    customer_ref: Mapped[str] = mapped_column(String(120))
    origin: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(200))

    scheduled_dispatch: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    promised_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estimated_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    priority: Mapped[DeliveryPriority] = mapped_column(
        Enum(DeliveryPriority, name="delivery_priority"), default=DeliveryPriority.NORMAL
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status"), default=DeliveryStatus.PENDING, index=True
    )

    vehicle_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True
    )

    distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    weather_exposure: Mapped[float] = mapped_column(Float, default=0.0)

    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    vehicle = relationship("Vehicle", back_populates="deliveries", foreign_keys=[vehicle_id])
