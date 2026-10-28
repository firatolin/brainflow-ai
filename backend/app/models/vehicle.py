from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VehicleType(str, enum.Enum):
    VAN = "van"
    TRUCK = "truck"
    MOTORBIKE = "motorbike"
    CAR = "car"


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "available"
    ON_ROUTE = "on_route"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType, name="vehicle_type"), default=VehicleType.VAN
    )
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(VehicleStatus, name="vehicle_status"), default=VehicleStatus.AVAILABLE, index=True
    )
    location_zone: Mapped[str] = mapped_column(String(120), default="central")
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    cost_per_km: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    deliveries = relationship("Delivery", back_populates="vehicle", foreign_keys="Delivery.vehicle_id")
