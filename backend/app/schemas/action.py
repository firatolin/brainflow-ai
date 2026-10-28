from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.operational_action import ActionStatus


class ActionRead(BaseModel):
    id: int
    action_type: str
    plan_id: Optional[int]
    status: ActionStatus
    before_state_json: str
    proposed_state_json: str
    expected_impact: str
    reason: str
    requested_at: datetime
    decided_at: Optional[datetime]
    executed_at: Optional[datetime]
    reviewer: Optional[str]
    execution_result: Optional[str]
    model_config = {"from_attributes": True}


class DecisionRequest(BaseModel):
    reviewer: Optional[str] = Field(default=None, max_length=120)
    note: Optional[str] = Field(default=None, max_length=2000)


class SubmitRequest(BaseModel):
    actor: Optional[str] = Field(default=None, max_length=120)


class ExecuteRequest(BaseModel):
    reviewer: Optional[str] = Field(default=None, max_length=120)
