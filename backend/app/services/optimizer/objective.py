"""Deterministic objective + feasibility for BrainFlow plan comparison.

All math is pure. Documented weights below.
"""
from __future__ import annotations

import time
from typing import Optional

from app.services.optimizer.plan_types import (
    PRIORITY_WEIGHT,
    Assignment,
    DeliverySnapshot,
    PlanMetrics,
    VehicleSnapshot,
)


# Default weights (documented; used in explanations & tests)
DEFAULT_WEIGHTS = {
    "late_count": 8.0,
    "priority_delay": 1.0,
    "total_delay": 0.2,
    "cost": 0.5,
    "changes": 2.0,
}

BALANCED_WEIGHTS = {
    **DEFAULT_WEIGHTS,
    "cost": 2.0,
    "total_delay": 0.35,
}

DEFAULT_SPEED_KMH = 25.0
MIN_ETA_MINUTES = 5.0

# Delay floor applied to "unassigned but not delivered" deliveries — captures
# the fact that an unassigned delivery cannot possibly arrive on time.
UNASSIGNED_DELAY_FLOOR_MIN = 30.0


def _travel_minutes(distance_km: float, weather_exposure: float) -> float:
    base = (max(distance_km, 0.5) / DEFAULT_SPEED_KMH) * 60.0
    base = max(base, MIN_ETA_MINUTES)
    return base * (1.0 + 0.6 * max(0.0, min(1.0, weather_exposure)))


def compute_expected_delay_minutes(
    delivery: DeliverySnapshot, *, now: float | None = None
) -> float:
    """Delay = max(0, expected_arrival - deadline). For unassigned, adds a floor."""
    if delivery.status in ("delivered", "cancelled", "failed"):
        return 0.0

    now_ts = now if now is not None else time.time()
    eta = _travel_minutes(delivery.distance_km, delivery.weather_exposure)
    # depart from max(now, dispatch)
    depart = max(now_ts, delivery.dispatch_ts)
    expected_arrival = depart + eta * 60.0
    delay = max(0.0, (expected_arrival - delivery.deadline_ts) / 60.0)

    if delivery.vehicle_id is None:
        # Unassigned cannot proceed — floor it
        delay = max(delay, UNASSIGNED_DELAY_FLOOR_MIN)
    return delay


def check_feasibility(
    assignments: list[Assignment],
    deliveries: dict[int, DeliverySnapshot],
    vehicles: dict[int, VehicleSnapshot],
) -> list[str]:
    reasons: set[str] = set()
    load: dict[int, int] = {}

    for a in assignments:
        if a.vehicle_id is None:
            continue
        v = vehicles.get(a.vehicle_id)
        if v is None:
            reasons.add(f"vehicle {a.vehicle_id} does not exist")
            continue
        if not v.available or v.status != "available":
            reasons.add(f"vehicle {v.code} is not available")
        d = deliveries.get(a.delivery_id)
        if d is None:
            continue
        if d.status in ("delivered", "cancelled", "failed"):
            continue
        load[v.id] = load.get(v.id, 0) + 1

    for vid, n in load.items():
        v = vehicles[vid]
        if n > v.capacity:
            reasons.add(f"vehicle {v.code} over capacity ({n}/{v.capacity})")

    return sorted(reasons)


def evaluate(
    assignments: list[Assignment],
    baseline: list[Assignment],
    deliveries: dict[int, DeliverySnapshot],
    vehicles: dict[int, VehicleSnapshot],
    weights: dict[str, float],
    *,
    now: float | None = None,
) -> PlanMetrics:
    base_map = {a.delivery_id: a.vehicle_id for a in baseline}
    assigned_map = {a.delivery_id: a.vehicle_id for a in assignments}
    now_ts = now if now is not None else time.time()

    late_count = 0
    total_delay = 0.0
    priority_delay = 0.0
    changes = 0
    additional_km = 0.0
    extra_cost = 0.0

    for did, d in deliveries.items():
        if d.status in ("delivered", "cancelled", "failed"):
            continue

        vid = assigned_map.get(did, base_map.get(did))
        # Build a synthetic snapshot reflecting the ASSIGNMENT (unassigned has vid=None)
        effective = DeliverySnapshot(
            id=d.id,
            priority=d.priority,
            status=d.status,
            vehicle_id=vid,
            distance_km=d.distance_km,
            deadline_ts=d.deadline_ts,
            dispatch_ts=d.dispatch_ts,
            weather_exposure=d.weather_exposure,
        )
        delay = compute_expected_delay_minutes(effective, now=now_ts)

        if delay > 0:
            late_count += 1
            total_delay += delay
            priority_delay += delay * PRIORITY_WEIGHT.get(d.priority, 0.5)

        prev_vid = base_map.get(did)
        if prev_vid != vid:
            changes += 1
            new_v = vehicles.get(vid) if vid is not None else None
            if new_v:
                additional_km += d.distance_km * 0.5
                extra_cost += new_v.cost_per_km * d.distance_km * 0.5

    reasons = check_feasibility(assignments, deliveries, vehicles)

    return PlanMetrics(
        late_count=late_count,
        total_delay_minutes=round(total_delay, 2),
        priority_weighted_delay=round(priority_delay, 2),
        extra_cost=round(extra_cost, 2),
        additional_travel_km=round(additional_km, 2),
        changes=changes,
        feasible=not reasons,
        infeasibility_reasons=reasons,
    )
