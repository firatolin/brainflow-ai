from datetime import datetime, timedelta, timezone

from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
from app.models.incident import Incident, IncidentStatus
from app.models.vehicle import Vehicle, VehicleStatus
from app.services import incident_service


def _now():
    return datetime.now(timezone.utc)


def _make_delivery(db, **over):
    now = _now()
    base = dict(
        tracking_number=f"T-{now.timestamp()}-{id(over)}",
        customer_ref="c",
        origin="A",
        destination="B",
        scheduled_dispatch=now - timedelta(minutes=5),
        promised_deadline=now + timedelta(hours=2),
        priority=DeliveryPriority.NORMAL,
        status=DeliveryStatus.PENDING,
        distance_km=10.0,
        cost_estimate=20.0,
        weather_exposure=0.0,
        updated_at=now,
    )
    base.update(over)
    d = Delivery(**base)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def test_detect_late_likely(db_session):
    d = _make_delivery(db_session, risk_score=80.0, status=DeliveryStatus.ASSIGNED)
    dets = incident_service.detect_all(db_session)
    kinds = {det.kind for det in dets if det.entity_id == d.id}
    assert "late_likely" in kinds


def test_detect_unassigned_urgent(db_session):
    d = _make_delivery(db_session, priority=DeliveryPriority.URGENT, status=DeliveryStatus.PENDING, vehicle_id=None)
    dets = incident_service.detect_all(db_session)
    kinds = {det.kind for det in dets if det.entity_id == d.id}
    assert "unassigned_high_priority" in kinds


def test_dedup_same_condition_across_scans(db_session):
    _make_delivery(db_session, risk_score=80.0, status=DeliveryStatus.ASSIGNED)
    dets1 = incident_service.detect_all(db_session)
    incident_service.apply(db_session, dets1)
    db_session.commit()

    before = db_session.query(Incident).count()
    # rerun without change
    dets2 = incident_service.detect_all(db_session)
    incident_service.apply(db_session, dets2)
    db_session.commit()
    after = db_session.query(Incident).count()
    assert before == after


def test_auto_resolve_when_condition_gone(db_session):
    d = _make_delivery(db_session, risk_score=80.0, status=DeliveryStatus.ASSIGNED)
    incident_service.apply(db_session, incident_service.detect_all(db_session))
    db_session.commit()

    # Clear the risk; rerun
    d.risk_score = 5.0
    db_session.commit()

    incident_service.apply(db_session, incident_service.detect_all(db_session))
    db_session.commit()

    # The late_likely for this delivery should now be RESOLVED
    inc = db_session.query(Incident).filter(
        Incident.kind == "late_likely", Incident.entity_id == d.id
    ).first()
    assert inc is not None
    assert inc.status == IncidentStatus.RESOLVED


def test_vehicle_unavailable_detected(db_session):
    v = Vehicle(code="VX", vehicle_type="van", capacity=5,
                status=VehicleStatus.MAINTENANCE, location_zone="central",
                available=False, cost_per_km=1.0)
    db_session.add(v)
    db_session.commit()
    db_session.refresh(v)

    _make_delivery(db_session, vehicle_id=v.id, status=DeliveryStatus.ASSIGNED)
    dets = incident_service.detect_all(db_session)
    kinds = {det.kind for det in dets}
    assert "vehicle_unavailable" in kinds
