from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScanRunRead(BaseModel):
    id: int
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    deliveries_scanned: int
    incidents_created: int
    incidents_reopened: int
    incidents_auto_resolved: int
    errors_json: str
    triggered_by: str

    model_config = {"from_attributes": True}
