"""Persists plan results from the pure optimizer into RecoveryPlan rows."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.delivery import Delivery, DeliveryStatus
from app.models.recovery_plan import PlanKind, PlanStatus, RecoveryPlan, RecoveryPlanItem
from app.models.vehicle import Vehicle
from app.services.optimizer.objective import compute_expected_delay_minutes
from app.services.optimizer.plan_types import DeliverySnapshot, PlanResult, VehicleSnapshot
from app.services.optimizer.planner import generate_plans


ACTIVE = (DeliveryStatus.PENDING, DeliveryStatus.ASSIGNED,
          DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELAYED)


def _build_snapshots(db: Session):
    deliveries: dict[int, DeliverySnapshot] = {}
    risks: dict[int, float] = {}
    for d in db.query(Delivery).filter(Delivery.status.in_(ACTIVE)).all():
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


def _kind_enum(kind_str: str) -> PlanKind:
    return {
        "baseline": PlanKind.BASELINE,
        "minimize_delays": PlanKind.MINIMIZE_DELAYS,
        "balanced": PlanKind.BALANCED,
    }[kind_str]


def generate_and_persist(db: Session) -> list[RecoveryPlan]:
    deliveries, vehicles, risks = _build_snapshots(db)
    results = generate_plans(deliveries, vehicles, risks)

    plans: list[RecoveryPlan] = []
    baseline_map = {d.id: d.vehicle_id for d in deliveries.values()}

    for r in results:
        plan = RecoveryPlan(
            kind=_kind_enum(r.kind),
            status=PlanStatus.DRAFT,
            current_plan_snapshot_json=json.dumps(
                {"assignments": {did: vid for did, vid in baseline_map.items()}}
            ),
            expected_late_count=r.metrics.late_count,
            expected_total_delay_minutes=r.metrics.total_delay_minutes,
            expected_priority_weighted_delay=r.metrics.priority_weighted_delay,
            expected_cost=r.metrics.extra_cost,
            expected_additional_travel_km=r.metrics.additional_travel_km,
            changes_count=r.metrics.changes,
            feasible=r.metrics.feasible,
            infeasibility_reasons_json=json.dumps(r.metrics.infeasibility_reasons),
            explanation=r.explanation,
        )
        db.add(plan)
        db.flush()

        for idx, a in enumerate(r.assignments):
            snap = deliveries.get(a.delivery_id)
            if snap is None:
                continue
            delay = compute_expected_delay_minutes(snap)
            db.add(RecoveryPlanItem(
                plan_id=plan.id,
                delivery_id=a.delivery_id,
                from_vehicle_id=baseline_map.get(a.delivery_id),
                to_vehicle_id=a.vehicle_id,
                sequence_position=idx,
                expected_delay_minutes=delay,
                expected_late=delay > 0,
            ))

    db.commit()
    for p in plans:
        db.refresh(p)
    # refresh loaded list from DB for relationship items
    return db.query(RecoveryPlan).order_by(RecoveryPlan.id.desc()).limit(len(results)).all()
