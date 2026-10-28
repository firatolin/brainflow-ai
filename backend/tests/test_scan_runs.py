from datetime import datetime, timedelta, timezone

from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
from app.models.scan_run import ScanRun
from app.services import scan_service


def _mk(db, status=DeliveryStatus.ASSIGNED, **over):
    now = datetime.now(timezone.utc)
    base = dict(
        tracking_number=f"T-{now.timestamp()}-{id(over)}",
        customer_ref="c", origin="A", destination="B",
        scheduled_dispatch=now - timedelta(minutes=5),
        promised_deadline=now + timedelta(hours=2),
        priority=DeliveryPriority.NORMAL,
        status=status, distance_km=10.0, cost_estimate=20.0,
        weather_exposure=0.0, updated_at=now,
    )
    base.update(over)
    d = Delivery(**base)
    db.add(d); db.commit(); db.refresh(d)
    return d


def test_scan_creates_scanrun_and_assessments(db_session):
    _mk(db_session, status=DeliveryStatus.ASSIGNED)
    _mk(db_session, status=DeliveryStatus.PENDING)
    run = scan_service.run_scan(db_session)
    assert run.status == "ok"
    assert run.deliveries_scanned >= 2
    assert run.finished_at is not None


def test_scan_populates_risk_scores(db_session):
    d = _mk(db_session, status=DeliveryStatus.ASSIGNED,
            promised_deadline=datetime.now(timezone.utc) - timedelta(hours=1))
    scan_service.run_scan(db_session)
    db_session.refresh(d)
    assert d.risk_score > 0
    assert d.risk_explanation is not None


def test_second_scan_dedups_incidents(db_session):
    _mk(db_session, status=DeliveryStatus.ASSIGNED, risk_score=80.0)
    scan_service.run_scan(db_session)
    from app.models.incident import Incident
    c1 = db_session.query(Incident).count()
    scan_service.run_scan(db_session)
    c2 = db_session.query(Incident).count()
    assert c1 == c2
