from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RiskFactorRead(BaseModel):
    name: str
    value: float
    # arbitrary extra keys allowed
    model_config = {"extra": "allow"}


class RiskResultRead(BaseModel):
    delivery_id: int
    score: float
    category: str
    confidence: float
    intervention: str
    factors: list[dict[str, Any]]
    assessed_at: datetime
