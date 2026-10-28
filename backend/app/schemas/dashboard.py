from typing import Any, Optional
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    totals: dict[str, Any]
    on_time_rate_pct: Optional[float]
    estimated_delay_exposure_minutes: float
    fleet: dict[str, Any]
    incidents: dict[str, Any]
    pending_approvals: int
    recent_events: list[dict[str, Any]]
    distributions: dict[str, Any]
    trend_7d: list[dict[str, Any]]
    generated_at: str
