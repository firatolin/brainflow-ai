"""Deterministic incident detection with stable identity-based dedup.

Dedup key = (kind, entity_type, entity_id, discriminator).
If a scan finds the same condition again, the existing OPEN or ACKNOWLEDGED
incident is left alone (no new row). If it was RESOLVED and the condition
has returned, it is reopened. If the condition no longer applies, an OPEN
incident is auto-resolved.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.vehicle import Vehicle, VehicleStatus


ACTIVE_DELIVERY_STATUSES = (
    DeliveryStatus.PENDING,
    DeliveryStatus.ASSIGNED,
    DeliveryStatus.IN_TRANSIT,
    DeliveryStatus.DELAYED,
)


@dataclass
class Detection:
    kind: str
    entity_type: str
    entity_id: int | None
    discriminator: str
    severity: IncidentSeverity
    title: str
    description: str
    evidence: dict
    suggested_action: str

    def identity(self) -> tuple:
        return (self.kind, self.entity_type, self.entity_id or 0, self.discriminator)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------- Detectors ----------

def detect_all(db: Session, now: datetime | None = None) -> list[Detection]:
    now = now or _now()
    detections: list[Detection] = []
    deliveries = db.query(Delivery).filter(Delivery.status.in_(ACTIVE_DELIVERY_STATUSES)).all()
    vehicles = db.query(Vehicle).all()
    veh_by_id = {v.id: v for v in vehicles}

    for d in deliveries:
        v = veh_by_id.get(d.vehicle_id) if d.vehicle_id else None

        # 1) late_likely (only if not already past delivered)
        if d.risk_score >= 50 and d.status != DeliveryStatus.DELIVERED:
            detections.append(Detection(
                kind="late_likely",
                entity_type="delivery",
                entity_id=d.id,
                discriminator="",
                severity=IncidentSeverity.HIGH if d.risk_score >= 75 else IncidentSeverity.MEDIUM,
                title=f"Delivery {d.tracking_number} likely late",
                description=(
                    f"Risk score {d.risk_score:.0f}/100 ({d.risk_explanation or 'rule-based estimate'})."
                ),
                evidence={"risk_score": d.risk_score, "deadline": _iso(d.promised_deadline)},
                suggested_action="Review recovery plan; consider reassignment or customer notice.",
            ))

        # 2) unassigned high priority
        if (
            d.vehicle_id is None
            and d.priority in (DeliveryPriority.HIGH, DeliveryPriority.URGENT)
            and d.status == DeliveryStatus.PENDING
        ):
            detections.append(Detection(
                kind="unassigned_high_priority",
                entity_type="delivery",
                entity_id=d.id,
                discriminator="",
                severity=IncidentSeverity.HIGH if d.priority == DeliveryPriority.URGENT else IncidentSeverity.MEDIUM,
                title=f"Unassigned {d.priority.value} priority: {d.tracking_number}",
                description="A high-priority delivery has no vehicle assigned.",
                evidence={"priority": d.priority.value},
                suggested_action="Assign an available vehicle immediately.",
            ))

        # 3) vehicle_unavailable (assigned but vehicle not available)
        if v is not None and (not v.available or v.status != VehicleStatus.AVAILABLE):
            detections.append(Detection(
                kind="vehicle_unavailable",
                entity_type="delivery",
                entity_id=d.id,
                discriminator=f"vehicle:{v.id}",
                severity=IncidentSeverity.HIGH,
                title=f"Delivery {d.tracking_number} on unavailable vehicle {v.code}",
                description=f"Vehicle {v.code} is {v.status.value}.",
                evidence={"vehicle_id": v.id, "vehicle_status": v.status.value},
                suggested_action="Reassign to an available vehicle.",
            ))

        # 4) severe_weather
        if (d.weather_exposure or 0.0) >= 0.5:
            detections.append(Detection(
                kind="severe_weather",
                entity_type="delivery",
                entity_id=d.id,
                discriminator="",
                severity=IncidentSeverity.MEDIUM,
                title=f"Severe weather exposure on {d.tracking_number}",
                description=f"Weather exposure {d.weather_exposure:.2f}.",
                evidence={"weather_exposure": d.weather_exposure},
                suggested_action="Add buffer time or reroute.",
            ))

        # 5) missing_info
        issues = []
        if d.scheduled_dispatch is None:
            issues.append("no_scheduled_dispatch")
        if d.promised_deadline is None:
            issues.append("no_deadline")
        if d.distance_km is None or d.distance_km <= 0:
            issues.append("no_distance")
        if issues:
            detections.append(Detection(
                kind="missing_info",
                entity_type="delivery",
                entity_id=d.id,
                discriminator=",".join(issues),
                severity=IncidentSeverity.LOW,
                title=f"Missing info: {d.tracking_number}",
                description=f"Issues: {', '.join(issues)}",
                evidence={"issues": issues},
                suggested_action="Fill in missing delivery fields.",
            ))

        # 6) stale_estimate
        upd = _as_aware(d.updated_at)
        if upd and (now - upd).total_seconds() > 6 * 3600 and d.status in ACTIVE_DELIVERY_STATUSES:
            detections.append(Detection(
                kind="stale_estimate",
                entity_type="delivery",
                entity_id=d.id,
                discriminator="",
                severity=IncidentSeverity.LOW,
                title=f"Stale estimate: {d.tracking_number}",
                description="Delivery hasn't been updated in >6h.",
                evidence={"updated_at": _iso(d.updated_at)},
                suggested_action="Refresh ETA or confirm status.",
            ))

    # 7) capacity_exceeded per vehicle
    for v in vehicles:
        active = [
            d for d in deliveries
            if d.vehicle_id == v.id and d.status in (
                DeliveryStatus.ASSIGNED, DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELAYED
            )
        ]
        if len(active) > v.capacity:
            detections.append(Detection(
                kind="capacity_exceeded",
                entity_type="vehicle",
                entity_id=v.id,
                discriminator="",
                severity=IncidentSeverity.HIGH,
                title=f"Vehicle {v.code} over capacity",
                description=f"{len(active)} active deliveries vs capacity {v.capacity}.",
                evidence={"active": len(active), "capacity": v.capacity},
                suggested_action="Rebalance deliveries across available vehicles.",
            ))

    return detections


# ---------- Persistence ----------

def apply(db: Session, detections: list[Detection]) -> dict:
    """Insert / reopen / auto-resolve. Returns counts."""
    now = _now()
    existing: dict[tuple, Incident] = {}
    for inc in db.query(Incident).all():
        existing[(inc.kind, inc.entity_type, inc.entity_id or 0, inc.discriminator)] = inc

    created = reopened = auto_resolved = 0
    seen_keys: set[tuple] = set()

    for det in detections:
        key = det.identity()
        seen_keys.add(key)
        inc = existing.get(key)

        if inc is None:
            db.add(Incident(
                kind=det.kind,
                entity_type=det.entity_type,
                entity_id=det.entity_id,
                discriminator=det.discriminator,
                severity=det.severity,
                status=IncidentStatus.OPEN,
                title=det.title,
                description=det.description,
                evidence_json=json.dumps(det.evidence),
                suggested_action=det.suggested_action,
            ))
            created += 1
        elif inc.status == IncidentStatus.RESOLVED:
            inc.status = IncidentStatus.OPEN
            inc.resolved_at = None
            inc.resolution_note = None
            inc.severity = det.severity
            inc.title = det.title
            inc.description = det.description
            inc.evidence_json = json.dumps(det.evidence)
            inc.suggested_action = det.suggested_action
            inc.updated_at = now
            reopened += 1
        else:
            # still open/acknowledged — refresh evidence, keep status
            inc.severity = det.severity
            inc.description = det.description
            inc.evidence_json = json.dumps(det.evidence)
            inc.updated_at = now

    # Auto-resolve OPEN incidents no longer detected
    for key, inc in existing.items():
        if key in seen_keys:
            continue
        if inc.status in (IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED):
            inc.status = IncidentStatus.RESOLVED
            inc.resolved_at = now
            inc.resolution_note = "auto-resolved: condition no longer detected"
            auto_resolved += 1

    db.flush()
    return {"created": created, "reopened": reopened, "auto_resolved": auto_resolved}


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
