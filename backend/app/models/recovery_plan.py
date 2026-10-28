from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlanKind(str, enum.Enum):
    BASELINE = "baseline"       # do nothing, current state
    MINIMIZE_DELAYS = "minimize_delays"
    BALANCED = "balanced"       # delay + cost trade-off


class PlanStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"     # sent to approvals
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class RecoveryPlan(Base):
    __tablename__ = "recovery_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[PlanKind] = mapped_column(Enum(PlanKind, name="plan_kind"), index=True)
    status: Mapped[PlanStatus] = mapped_column(
        Enum(PlanStatus, name="plan_status"), default=PlanStatus.DRAFT, index=True
    )

    # Snapshots — inputs as they were when generated (so we can detect drift later)
    current_plan_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")

    # Metrics
    expected_late_count: Mapped[int] = mapped_column(Integer, default=0)
    expected_total_delay_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    expected_priority_weighted_delay: Mapped[float] = mapped_column(Float, default=0.0)
    expected_cost: Mapped[float] = mapped_column(Float, default=0.0)
    expected_additional_travel_km: Mapped[float] = mapped_column(Float, default=0.0)
    changes_count: Mapped[int] = mapped_column(Integer, default=0)
    feasible: Mapped[bool] = mapped_column(default=True)
    infeasibility_reasons_json: Mapped[str] = mapped_column(Text, default="[]")

    explanation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    items = relationship("RecoveryPlanItem", back_populates="plan",
                         cascade="all, delete-orphan", order_by="RecoveryPlanItem.id")


class RecoveryPlanItem(Base):
    __tablename__ = "recovery_plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("recovery_plans.id", ondelete="CASCADE"), index=True)
    delivery_id: Mapped[int] = mapped_column(Integer, index=True)
    from_vehicle_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    to_vehicle_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sequence_position: Mapped[int] = mapped_column(Integer, default=0)
    expected_delay_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    expected_late: Mapped[bool] = mapped_column(default=False)

    plan = relationship("RecoveryPlan", back_populates="items")
