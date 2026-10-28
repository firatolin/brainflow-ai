from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_id: Mapped[int] = mapped_column(
        ForeignKey("deliveries.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float)          # 0..100
    category: Mapped[str] = mapped_column(String(20))    # low|medium|high|critical
    confidence: Mapped[float] = mapped_column(Float)     # 0..1 (data-quality)
    intervention: Mapped[str] = mapped_column(String(40))
    factors_json: Mapped[str] = mapped_column(Text)      # JSON string of factor breakdown
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
