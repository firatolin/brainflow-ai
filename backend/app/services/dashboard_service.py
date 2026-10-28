"""Dashboard summary — all values derived from persisted records.

Nothing here is hardcoded. Empty datasets return zeros, not errors.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.approval import ApprovalDecision
from app.models.audit_event import AuditEvent
from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
from app.models.incident import Incident, IncidentStatus
from app.models.operational_action import ActionStatus, OperationalAction
from app.models.vehicle import Vehicle, VehicleStatus


ACTIVE = (DeliveryStatus.PENDING, DeliveryStatus.ASSIGNED,
          DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELAYED)
TERMINAL = (DeliveryStatus.DELIVERED, DeliveryStatus.FAILED, DeliveryStatus.CANCELLED)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def summary(db: Session) -> dict:
    now = _now()

    total = db.query(func.count(Delivery.id)).scalar() or 0
    active = db.query(func.count(Delivery.id)).filter(Delivery.status.in_(ACTIVE)).scalar() or 0
    at_risk = db.query(func.count(Delivery.id)).filter(
        Delivery.status.in_(ACTIVE), Delivery.risk_score >= 50.0
    ).scalar() or 0
    critical_risk = db.query(func.count(Delivery.id)).filter(
        Delivery.status.in_(ACTIVE), Delivery.risk_score >= 75.0
    ).scalar() or 0
    delayed = db.query(func.count(Delivery.id)).filter(
        Delivery.status == DeliveryStatus.DELAYED
    ).scalar() or 0

    delivered = db.query(func.count(Delivery.id)).filter(
        Delivery.status == DeliveryStatus.DELIVERED
    ).scalar() or 0
    completed = db.query(func.count(Delivery.id)).filter(
        Delivery.status.in_((DeliveryStatus.DELIVERED, DeliveryStatus.FAILED))
    ).scalar() or 0

    # on-time = delivered where actual_arrival <= promised_deadline
    on_time_q = (
        db.query(func.count(Delivery.id))
        .filter(Delivery.status == DeliveryStatus.DELIVERED)
        .filter(Delivery.actual_arrival.is_not(None))
        .filter(Delivery.actual_arrival <= Delivery.promised_deadline)
        .scalar()
    ) or 0
    on_time_rate = round((on_time_q / delivered * 100.0), 2) if delivered else None

    # estimated delay exposure minutes: sum of (deadline - now) for at-risk deliveries,
    # floored at 0. This is an estimate, not a measured outcome.
    delay_exposure_minutes = 0.0
    risk_rows = (
        db.query(Delivery)
        .filter(Delivery.status.in_(ACTIVE), Delivery.risk_score >= 50.0)
        .all()
    )
    for d in risk_rows:
        if d.promised_deadline is None:
            continue
        dl = d.promised_deadline if d.promised_deadline.tzinfo else d.promised_deadline.replace(tzinfo=timezone.utc)
        remaining = (dl - now).total_seconds() / 60.0
        # exposure = remaining time when already at risk (bounded by 4h)
        delay_exposure_minutes += max(0.0, min(remaining, 240.0))

    # vehicles
    total_vehicles = db.query(func.count(Vehicle.id)).scalar() or 0
    active_vehicles = db.query(func.count(Vehicle.id)).filter(
        Vehicle.available == True,  # noqa: E712
        Vehicle.status == VehicleStatus.AVAILABLE,
    ).scalar() or 0

    # incidents
    open_incidents = db.query(func.count(Incident.id)).filter(
        Incident.status == IncidentStatus.OPEN
    ).scalar() or 0
    acknowledged_incidents = db.query(func.count(Incident.id)).filter(
        Incident.status == IncidentStatus.ACKNOWLEDGED
    ).scalar() or 0

    # pending approvals
    pending_approvals = db.query(func.count(OperationalAction.id)).filter(
        OperationalAction.status == ActionStatus.PENDING_APPROVAL
    ).scalar() or 0

    # recent events (audit)
    recent_events_rows = (
        db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(10).all()
    )
    recent_events = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "actor": e.actor,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in recent_events_rows
    ]

    # distributions
    status_dist = {
        s.value: db.query(func.count(Delivery.id)).filter(Delivery.status == s).scalar() or 0
        for s in DeliveryStatus
    }
    risk_buckets = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    risk_rows_all = db.query(Delivery).filter(Delivery.status.in_(ACTIVE)).all()
    for d in risk_rows_all:
        if d.risk_score < 25:
            risk_buckets["low"] += 1
        elif d.risk_score < 50:
            risk_buckets["medium"] += 1
        elif d.risk_score < 75:
            risk_buckets["high"] += 1
        else:
            risk_buckets["critical"] += 1

    # 7-day operational trend: deliveries created / delivered per day
    trend = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        created = db.query(func.count(Delivery.id)).filter(
            Delivery.created_at >= day_start, Delivery.created_at < day_end
        ).scalar() or 0
        completed_today = db.query(func.count(Delivery.id)).filter(
            Delivery.status == DeliveryStatus.DELIVERED,
            Delivery.updated_at >= day_start, Delivery.updated_at < day_end,
        ).scalar() or 0
        trend.append({
            "date": day_start.date().isoformat(),
            "created": created,
            "delivered": completed_today,
        })

    return {
        "totals": {
            "deliveries": total,
            "active_deliveries": active,
            "at_risk": at_risk,
            "critical_risk": critical_risk,
            "delayed": delayed,
            "delivered": delivered,
            "completed": completed,
        },
        "on_time_rate_pct": on_time_rate,
        "estimated_delay_exposure_minutes": round(delay_exposure_minutes, 2),
        "fleet": {
            "total": total_vehicles,
            "active": active_vehicles,
        },
        "incidents": {
            "open": open_incidents,
            "acknowledged": acknowledged_incidents,
        },
        "pending_approvals": pending_approvals,
        "recent_events": recent_events,
        "distributions": {
            "status": status_dist,
            "risk": risk_buckets,
        },
        "trend_7d": trend,
        "generated_at": now.isoformat(),
    }
