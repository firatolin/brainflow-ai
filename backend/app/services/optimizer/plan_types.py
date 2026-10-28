from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


PRIORITY_WEIGHT = {"low": 0.25, "normal": 0.5, "high": 1.0, "urgent": 2.0}


@dataclass
class DeliverySnapshot:
    id: int
    priority: str
    status: str
    vehicle_id: Optional[int]
    distance_km: float
    deadline_ts: float        # unix epoch seconds
    dispatch_ts: float
    weather_exposure: float


@dataclass
class VehicleSnapshot:
    id: int
    code: str
    capacity: int
    available: bool
    status: str
    cost_per_km: float


@dataclass
class Assignment:
    delivery_id: int
    vehicle_id: Optional[int]
    sequence_position: int = 0


@dataclass
class PlanMetrics:
    late_count: int
    total_delay_minutes: float
    priority_weighted_delay: float
    extra_cost: float
    additional_travel_km: float
    changes: int
    feasible: bool
    infeasibility_reasons: list[str] = field(default_factory=list)


@dataclass
class PlanResult:
    kind: str
    assignments: list[Assignment]
    metrics: PlanMetrics
    explanation: str
