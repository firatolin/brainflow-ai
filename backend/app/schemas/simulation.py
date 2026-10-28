from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.simulation import SimulationScenario


class SimulationCreate(BaseModel):
    scenario: SimulationScenario
    params: dict[str, Any] = {}


class SimulationRead(BaseModel):
    id: int
    scenario: SimulationScenario
    params_json: str
    baseline_metrics_json: str
    simulated_metrics_json: str
    diff_json: str
    explanation: str
    created_at: datetime
    model_config = {"from_attributes": True}
