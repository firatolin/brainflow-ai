from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditEventRead(BaseModel):
    id: int
    event_type: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    actor: str
    context_json: str
    created_at: datetime
    model_config = {"from_attributes": True}
