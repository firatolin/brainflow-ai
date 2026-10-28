"""What-if simulator. Operates on in-memory snapshots. Never mutates DB rows."""
from __future__ import annotations

import time
from dataclasses import replace

from sqlalchemy.orm import Session

from app.models.delivery import Delivery, DeliveryStatus
from app.models.vehicle import Vehicle
from app.services.optimizer.objective import (
    DEFAULT_WEIGHTS,
    check_feasibility,
    compute_expected_delay_minutes,
    evaluate,
)
from app.services.optimizer.plan_types import (
    Assignment,
    DeliverySnapshot,
    VehicleSnapshot,
)
from app.services.optimizer.planner import generate_plans


def _snapshot(db: Session):
    deliveries: dict[int, DeliverySnapshot] = {}
    risks: dict[int, float] = {}
    for d in db.query(Delivery).filter(Delivery.status.in_(
        [DeliveryStatus.PENDING, DeliveryStatus.ASSIGNED,
         DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELAYED]
    )).all():
        deliveries[d.id] = DeliverySnapshot(
            id=d.id,
            priority=d.priority.value,
            status=d.status.value,
            vehicle_id=d.vehicle_id,
            distance_km=d.distance_km or 0.0,
            deadline_ts=d.promised_deadline.timestamp(),
            dispatch_ts=d.scheduled_dispatch.timestamp(),
            weather_exposure=d.weather_exposure or 0.0,
        )
        risks[d.id] = d.risk_score or 0.0

    vehicles: dict[int, VehicleSnapshot] = {}
    for v in db.query(Vehicle).all():
        vehicles[v.id] = VehicleSnapshot(
            id=v.id, code=v.code, capacity=v.capacity,
            available=v.available, status=v.status.value,
            cost_per_km=v.cost_per_km,
        )
    return deliveries, vehicles, risks


def _apply_scenario(scenario: str, params: dict, deliveries, vehicles):
    deliveries = dict(deliveries)
    vehicles = dict(vehicles)
    note = ""

    if scenario == "vehicle_unavailable":
        vid = int(params.get("vehicle_id", 0))
        v = vehicles.get(vid)
        if not v:
            raise ValueError(f"vehicle {vid} not found")
        vehicles[vid] = replace(v, available=False, status="maintenance")
        note = f"Vehicle {v.code} marked unavailable."

    elif scenario == "heavy_rain":
        bump = float(params.get("weather_delta", 0.4))
        for did, d in deliveries.items():
            deliveries[did] = replace(d, weather_exposure=min(1.0, d.weather_exposure + bump))
        note = f"Increased weather exposure by {bump} on all active deliveries."

    elif scenario == "urgent_added":
        new_id = -1
        deliveries[new_id] = DeliverySnapshot(
            id=new_id,
            priority="urgent",
            status="pending",
            vehicle_id=None,
            distance_km=float(params.get("distance_km", 10.0)),
            deadline_ts=float(params.get("deadline_ts", 0.0)) or time.time() + 3600,
            dispatch_ts=time.time(),
            weather_exposure=float(params.get("weather_exposure", 0.3)),
        )
        note = "Hypothetical urgent delivery injected."

    elif scenario == "capacity_change":
        vid = int(params.get("vehicle_id", 0))
        new_cap = int(params.get("capacity", 0))
        v = vehicles.get(vid)
        if not v:
            raise ValueError(f"vehicle {vid} not found")
        vehicles[vid] = replace(v, capacity=new_cap)
        note = f"Vehicle {v.code} capacity changed to {new_cap}."

    elif scenario == "deadline_earlier":
        did = int(params.get("delivery_id", 0))
        delta_min = float(params.get("minutes_earlier", 60))
        d = deliveries.get(did)
        if not d:
            raise ValueError(f"delivery {did} not found")
        deliveries[did] = replace(d, deadline_ts=d.deadline_ts - delta_min * 60.0)
        note = f"Delivery {did} deadline moved {delta_min:.0f} min earlier."

    elif scenario == "assignment_failed":
        did = int(params.get("delivery_id", 0))
        d = deliveries.get(did)
        if not d:
            raise ValueError(f"delivery {did} not found")
        deliveries[did] = replace(d, vehicle_id=None, status="pending")
        note = f"Delivery {did} assignment failed; reverted to pending."

    else:
        raise ValueError(f"Unknown scenario '{scenario}'")

    return deliveries, vehicles, note


def _metrics_from_assignments(deliveries, vehicles) -> dict:
    """Metric triple assuming the deliveries' own vehicle_id is used."""
    assignments = [Assignment(d.id, d.vehicle_id) for d in deliveries.values()]
    m = evaluate(assignments, assignments, deliveries, vehicles, DEFAULT_WEIGHTS)
    return {
        "late_count": m.late_count,
        "total_delay_minutes": m.total_delay_minutes,
        "priority_weighted_delay": m.priority_weighted_delay,
        "extra_cost": m.extra_cost,
        "feasible": m.feasible,
        "infeasibility_reasons": m.infeasibility_reasons,
    }


def run_simulation(db: Session, scenario: str, params: dict) -> dict:
    base_d, base_v, base_risks = _snapshot(db)

    # 1) baseline metrics
    baseline_metrics = _metrics_from_assignments(base_d, base_v)

    # 2) apply scenario
    sim_d, sim_v, note = _apply_scenario(scenario, params, base_d, base_v)

    # 3) simulated WITHOUT recovery = metrics on the scenario snapshot using
    #    the existing (now possibly broken) assignments
    simulated_no_recovery = _metrics_from_assignments(sim_d, sim_v)

    # 4) run planner on scenario snapshot to get recovery plan
    plans = generate_plans(sim_d, sim_v, base_risks)
    minimize = next((p for p in plans if p.kind == "minimize_delays"), None)
    recovered_metrics = (
        {
            "late_count": minimize.metrics.late_count,
            "total_delay_minutes": minimize.metrics.total_delay_minutes,
            "priority_weighted_delay": minimize.metrics.priority_weighted_delay,
            "extra_cost": minimize.metrics.extra_cost,
            "feasible": minimize.metrics.feasible,
            "infeasibility_reasons": minimize.metrics.infeasibility_reasons,
            "assignments_changed": minimize.metrics.changes,
        }
        if minimize
        else simulated_no_recovery
    )

    # 5) diff against baseline
    diff = {
        "no_recovery_late_delta": simulated_no_recovery["late_count"] - baseline_metrics["late_count"],
        "no_recovery_delay_delta": round(
            simulated_no_recovery["total_delay_minutes"] - baseline_metrics["total_delay_minutes"], 2
        ),
        "recovered_late_delta": recovered_metrics["late_count"] - baseline_metrics["late_count"],
        "recovered_delay_delta": round(
            recovered_metrics["total_delay_minutes"] - baseline_metrics["total_delay_minutes"], 2
        ),
        "assignments_changed_by_recovery": recovered_metrics.get("assignments_changed", 0),
        "baseline_feasible": baseline_metrics["feasible"],
        "no_recovery_feasible": simulated_no_recovery["feasible"],
        "recovered_feasible": recovered_metrics["feasible"],
        "no_recovery_infeasibility_reasons": simulated_no_recovery["infeasibility_reasons"],
        "recovered_infeasibility_reasons": recovered_metrics["infeasibility_reasons"],
    }

    explanation = (
        f"Simulation: {note} "
        f"Baseline: late={baseline_metrics['late_count']}, "
        f"delay={baseline_metrics['total_delay_minutes']:.0f}min. "
        f"Scenario without recovery: late={simulated_no_recovery['late_count']}, "
        f"delay={simulated_no_recovery['total_delay_minutes']:.0f}min, "
        f"feasible={simulated_no_recovery['feasible']}. "
        f"With recovery plan: late={recovered_metrics['late_count']}, "
        f"delay={recovered_metrics['total_delay_minutes']:.0f}min, "
        f"feasible={recovered_metrics['feasible']}, "
        f"changes={recovered_metrics.get('assignments_changed', 0)}. "
        "Estimated outcomes only; no production state was modified."
    )

    return {
        "scenario": scenario,
        "params": params,
        "baseline_metrics": baseline_metrics,
        "simulated_metrics": simulated_no_recovery,
        "recovered_metrics": recovered_metrics,
        "diff": diff,
        "explanation": explanation,
    }
