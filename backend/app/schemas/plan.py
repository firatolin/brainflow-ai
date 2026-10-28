from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.recovery_plan import PlanKind, PlanStatus


class PlanItemRead(BaseModel):
    id: int
    delivery_id: int
    from_vehicle_id: Optional[int]
    to_vehicle_id: Optional[int]
    sequence_position: int
    expected_delay_minutes: float
    expected_late: bool
    model_config = {"from_attributes": True}


class PlanRead(BaseModel):
    id: int
    kind: PlanKind
    status: PlanStatus
    expected_late_count: int
    expected_total_delay_minutes: float
    expected_priority_weighted_delay: float
    expected_cost: float
    expected_additional_travel_km: float
    changes_count: int
    feasible: bool
    infeasibility_reasons_json: str
    explanation: str
    created_at: datetime
    items: list[PlanItemRead] = []
    model_config = {"from_attributes": True}


class PlanGenerateRequest(BaseModel):
    pass  # operates on current DB state
