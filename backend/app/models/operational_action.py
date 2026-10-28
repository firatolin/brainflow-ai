from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ActionStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class OperationalAction(Base):
    """A single proposed operational change (e.g., a recovery plan)."""

    __tablename__ = "operational_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action_type: Mapped[str] = mapped_column(String(60), default="recovery_plan")
    plan_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recovery_plans.id", ondelete="SET NULL"), nullable=True, index=True
    )

    status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus, name="action_status"),
        default=ActionStatus.PENDING_APPROVAL,
        index=True,
    )

    before_state_json: Mapped[str] = mapped_column(Text, default="{}")
    proposed_state_json: Mapped[str] = mapped_column(Text, default="{}")
    expected_impact: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewer: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    execution_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
