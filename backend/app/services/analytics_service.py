"""Historical analytics — all derived from persisted outcomes.

Distinguishes measured historical outcomes from simulated metrics explicitly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.delivery import Delivery, DeliveryStatus
from app.models.incident import Incident, IncidentStatus
from app.models.recovery_plan import PlanKind, RecoveryPlan
from app.models.simulation import Simulation
from app.models.vehicle import Vehicle, VehicleStatus


ACTIVE = (DeliveryStatus.PENDING, DeliveryStatus.ASSIGNED,
          DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELAYED)
DELIVERED_OR_FAILED = (DeliveryStatus.DELIVERED, DeliveryStatus.FAILED)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def summary(db: Session) -> dict:
    now = _now()

    total = db.query(func.count(Delivery.id)).scalar() or 0
    delivered_q = db.query(Delivery).filter(Delivery.status == DeliveryStatus.DELIVERED).all()
    failed_q = db.query(func.count(Delivery.id)).filter(
        Delivery.status == DeliveryStatus.FAILED
    ).scalar() or 0
    cancelled_q = db.query(func.count(Delivery.id)).filter(
        Delivery.status == DeliveryStatus.CANCELLED
    ).scalar() or 0

    delivered = len(delivered_q)
    completed = delivered + failed_q + cancelled_q
    completion_rate = round(delivered / completed * 100.0, 2) if completed else None

    # on-time and delay rates
    on_time = 0
    delay_minutes_list: list[float] = []
    for d in delivered_q:
        if d.actual_arrival and d.promised_deadline:
            a = _as_aware(d.actual_arrival)
            p = _as_aware(d.promised_deadline)
            if a and p:
                if a <= p:
                    on_time += 1
                else:
                    delay_minutes_list.append((a - p).total_seconds() / 60.0)

    on_time_rate = round(on_time / delivered * 100.0, 2) if delivered else None
    delayed_count = len(delay_minutes_list)
    delay_rate = round(delayed_count / delivered * 100.0, 2) if delivered else None
    avg_delay_minutes = (
        round(sum(delay_minutes_list) / delayed_count, 2) if delayed_count else None
    )

    # risk distribution (active only)
    risk_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for d in db.query(Delivery).filter(Delivery.status.in_(ACTIVE)).all():
        if d.risk_score < 25:
            risk_dist["low"] += 1
        elif d.risk_score < 50:
            risk_dist["medium"] += 1
        elif d.risk_score < 75:
            risk_dist["high"] += 1
        else:
            risk_dist["critical"] += 1

    # incident frequency
    incidents_total = db.query(func.count(Incident.id)).scalar() or 0
    incidents_by_kind = dict(
        db.query(Incident.kind, func.count(Incident.id))
        .group_by(Incident.kind).all()
    )

    # incident resolution time (avg minutes for RESOLVED)
    resolved = db.query(Incident).filter(Incident.status == IncidentStatus.RESOLVED).all()
    resolution_times = []
    for inc in resolved:
        c = _as_aware(inc.created_at)
        r = _as_aware(inc.resolved_at)
        if c and r:
            resolution_times.append((r - c).total_seconds() / 60.0)
    avg_resolution_minutes = (
        round(sum(resolution_times) / len(resolution_times), 2) if resolution_times else None
    )

    # vehicle utilization: active deliveries per available vehicle (capacity-normalized)
    vehicles = db.query(Vehicle).all()
    utilization = []
    active_dels_by_vehicle: dict[int, int] = {}
    for d in db.query(Delivery).filter(Delivery.status.in_(ACTIVE)).all():
        if d.vehicle_id is not None:
            active_dels_by_vehicle[d.vehicle_id] = active_dels_by_vehicle.get(d.vehicle_id, 0) + 1
    for v in vehicles:
        load = active_dels_by_vehicle.get(v.id, 0)
        util_pct = round(min(100.0, load / v.capacity * 100.0), 2) if v.capacity else 0.0
        utilization.append({
            "vehicle_id": v.id,
            "code": v.code,
            "capacity": v.capacity,
            "active": load,
            "available": v.available and v.status == VehicleStatus.AVAILABLE,
            "utilization_pct": util_pct,
        })

    # cost estimate: sum of cost_estimate for active deliveries
    estimated_cost_active = (
        db.query(func.sum(Delivery.cost_estimate))
        .filter(Delivery.status.in_(ACTIVE)).scalar()
    ) or 0.0
    estimated_cost_delivered = (
        db.query(func.sum(Delivery.cost_estimate))
        .filter(Delivery.status == DeliveryStatus.DELIVERED).scalar()
    ) or 0.0

    # plan comparison: latest plans with metrics
    plans = (
        db.query(RecoveryPlan)
        .order_by(RecoveryPlan.id.desc())
        .limit(9)
        .all()
    )
    plan_comparison = [
        {
            "id": p.id,
            "kind": p.kind.value,
            "feasible": p.feasible,
            "late_count": p.expected_late_count,
            "total_delay_minutes": p.expected_total_delay_minutes,
            "extra_cost": p.expected_cost,
            "changes": p.changes_count,
        }
        for p in plans
    ]

    # 14-day trend of delivered vs delayed
    trend = []
    for i in range(13, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        deliv = db.query(func.count(Delivery.id)).filter(
            Delivery.status == DeliveryStatus.DELIVERED,
            Delivery.updated_at >= day_start, Delivery.updated_at < day_end,
        ).scalar() or 0
        incs = db.query(func.count(Incident.id)).filter(
            Incident.created_at >= day_start, Incident.created_at < day_end
        ).scalar() or 0
        trend.append({"date": day_start.date().isoformat(), "delivered": deliv, "incidents": incs})

    # simulation count
    simulations_count = db.query(func.count(Simulation.id)).scalar() or 0

    return {
        "measured": {
            "note": "Measured historical outcomes from persisted records.",
            "total_deliveries": total,
            "delivered": delivered,
            "failed": failed_q,
            "cancelled": cancelled_q,
            "completion_rate_pct": completion_rate,
            "on_time_rate_pct": on_time_rate,
            "delay_rate_pct": delay_rate,
            "avg_delay_minutes": avg_delay_minutes,
            "cost_estimate_active": round(float(estimated_cost_active), 2),
            "cost_estimate_delivered": round(float(estimated_cost_delivered), 2),
        },
        "estimated": {
            "note": "Rule-based estimates over current state; not statistically trained.",
            "risk_distribution": risk_dist,
            "vehicle_utilization": utilization,
        },
        "incidents": {
            "total": incidents_total,
            "by_kind": incidents_by_kind,
            "avg_resolution_minutes": avg_resolution_minutes,
        },
        "plans": plan_comparison,
        "simulations": {
            "count": simulations_count,
            "note": "Simulations are hypothetical; never applied to production state.",
        },
        "trend_14d": trend,
        "generated_at": now.isoformat(),
    }
