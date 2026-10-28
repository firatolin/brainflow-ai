from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.delivery import Delivery, DeliveryStatus
from app.models.risk_assessment import RiskAssessment
from app.models.scan_run import ScanRun
from app.models.vehicle import Vehicle
from app.services import incident_service, risk_engine


ACTIVE_STATUSES = (
    DeliveryStatus.PENDING,
    DeliveryStatus.ASSIGNED,
    DeliveryStatus.IN_TRANSIT,
    DeliveryStatus.DELAYED,
)


def run_scan(db: Session, *, triggered_by: str = "manual") -> ScanRun:
    """Perform a full scan: score active deliveries, persist assessments,
    detect incidents with dedup, record ScanRun."""
    run = ScanRun(status="running", triggered_by=triggered_by)
    db.add(run)
    db.flush()

    now = datetime.now(timezone.utc)
    errors: list[str] = []
    scanned = 0

    try:
        deliveries = db.query(Delivery).filter(Delivery.status.in_(ACTIVE_STATUSES)).all()
        vehicles = {v.id: v for v in db.query(Vehicle).all()}

        for d in deliveries:
            try:
                vehicle = vehicles.get(d.vehicle_id) if d.vehicle_id else None
                result = risk_engine.assess(d, vehicle, now=now)

                d.risk_score = result.score
                d.risk_explanation = (
                    f"rule-based; category={result.category}; "
                    f"confidence={result.confidence:.2f}; intervention={result.intervention}"
                )

                db.add(RiskAssessment(
                    delivery_id=d.id,
                    score=result.score,
                    category=result.category,
                    confidence=result.confidence,
                    intervention=result.intervention,
                    factors_json=json.dumps(result.factors),
                    assessed_at=now,
                ))
                scanned += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"delivery {d.id}: {exc}")
                traceback.print_exc()

        # Incident detection requires the freshly persisted risk_scores
        db.flush()
        detections = incident_service.detect_all(db, now=now)
        counts = incident_service.apply(db, detections)

        run.deliveries_scanned = scanned
        run.incidents_created = counts["created"]
        run.incidents_reopened = counts["reopened"]
        run.incidents_auto_resolved = counts["auto_resolved"]
        run.errors_json = json.dumps(errors)
        run.status = "ok" if not errors else "failed"
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        # recreate run to persist failure (rollback wiped flush)
        run = ScanRun(
            status="failed",
            triggered_by=triggered_by,
            errors_json=json.dumps([f"scan aborted: {exc}"]),
        )
        db.add(run)
        db.flush()
    finally:
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)

    return run
