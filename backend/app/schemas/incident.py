from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.incident import IncidentSeverity, IncidentStatus


class IncidentRead(BaseModel):
    id: int
    kind: str
    entity_type: str
    entity_id: Optional[int]
    discriminator: str
    severity: IncidentSeverity
    status: IncidentStatus
    title: str
    description: str
    evidence_json: str
    suggested_action: str
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolution_note: Optional[str]

    model_config = {"from_attributes": True}


class IncidentUpdate(BaseModel):
    status: IncidentStatus
    resolution_note: Optional[str] = Field(default=None, max_length=1000)
