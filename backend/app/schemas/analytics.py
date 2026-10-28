from typing import Any
from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    measured: dict[str, Any]
    estimated: dict[str, Any]
    incidents: dict[str, Any]
    plans: list[dict[str, Any]]
    simulations: dict[str, Any]
    trend_14d: list[dict[str, Any]]
    generated_at: str
