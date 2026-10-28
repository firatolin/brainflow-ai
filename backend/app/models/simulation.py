from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SimulationScenario(str, enum.Enum):
    VEHICLE_UNAVAILABLE = "vehicle_unavailable"
    HEAVY_RAIN = "heavy_rain"
    URGENT_ADDED = "urgent_added"
    CAPACITY_CHANGE = "capacity_change"
    DEADLINE_EARLIER = "deadline_earlier"
    ASSIGNMENT_FAILED = "assignment_failed"


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario: Mapped[SimulationScenario] = mapped_column(
        Enum(SimulationScenario, name="simulation_scenario"), index=True
    )
    params_json: Mapped[str] = mapped_column(Text, default="{}")

    baseline_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    simulated_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    diff_json: Mapped[str] = mapped_column(Text, default="{}")
    explanation: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
