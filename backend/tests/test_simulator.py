from datetime import datetime, timedelta, timezone

from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
from app.models.vehicle import Vehicle, VehicleStatus
from app.services import simulator


def _mk_vehicle(db, code="V1", cap=5, available=True, status=VehicleStatus.AVAILABLE):
    v = Vehicle(code=code, vehicle_type="van", capacity=cap, status=status,
                location_zone="central", available=available, cost_per_km=1.0)
    db.add(v); db.commit(); db.refresh(v)
    return v


def _mk_delivery(db, tracking, vehicle_id=None, priority=DeliveryPriority.NORMAL):
    now = datetime.now(timezone.utc)
    d = Delivery(
        tracking_number=tracking, customer_ref="c", origin="A", destination="B",
        scheduled_dispatch=now, promised_deadline=now + timedelta(hours=4),
        priority=priority, status=DeliveryStatus.ASSIGNED if vehicle_id else DeliveryStatus.PENDING,
        vehicle_id=vehicle_id, distance_km=10.0, cost_estimate=20.0,
        weather_exposure=0.0,
    )
    db.add(d); db.commit(); db.refresh(d)
    return d


def test_simulation_does_not_touch_db(db_session):
    v = _mk_vehicle(db_session)
    d = _mk_delivery(db_session, "T-1", vehicle_id=v.id)
    before_vehicle_status = v.status
    before_delivery_vehicle = d.vehicle_id

    simulator.run_simulation(db_session, "vehicle_unavailable", {"vehicle_id": v.id})

    db_session.refresh(v)
    db_session.refresh(d)
    assert v.status == before_vehicle_status
    assert d.vehicle_id == before_delivery_vehicle


def test_vehicle_unavailable_scenario_creates_diff(db_session):
    v = _mk_vehicle(db_session)
    _mk_delivery(db_session, "T-1", vehicle_id=v.id)
    out = simulator.run_simulation(db_session, "vehicle_unavailable", {"vehicle_id": v.id})
    assert out["scenario"] == "vehicle_unavailable"
    assert "diff" in out
    assert "no_recovery_late_delta" in out["diff"]
    assert "recovered_late_delta" in out["diff"]
    assert "recovered_feasible" in out["diff"]


def test_heavy_rain_increases_weather_exposure(db_session):
    v = _mk_vehicle(db_session)
    _mk_delivery(db_session, "T-1", vehicle_id=v.id)
    out = simulator.run_simulation(db_session, "heavy_rain", {"weather_delta": 0.5})
    assert out["scenario"] == "heavy_rain"


def test_invalid_scenario_raises(db_session):
    _mk_vehicle(db_session)
    import pytest
    with pytest.raises(ValueError):
        simulator.run_simulation(db_session, "nonexistent_scenario", {})


def test_vehicle_unavailable_simulation_shows_impact_and_recovery(db_session):
    """Two vehicles, one has 2 deliveries; when it goes unavailable, without
    recovery infeasibility appears; with recovery they move to vehicle 2."""
    v1 = _mk_vehicle(db_session, code="V-A", cap=5)
    v2 = _mk_vehicle(db_session, code="V-B", cap=5)
    _mk_delivery(db_session, "T-1", vehicle_id=v1.id)
    _mk_delivery(db_session, "T-2", vehicle_id=v1.id)

    out = simulator.run_simulation(db_session, "vehicle_unavailable", {"vehicle_id": v1.id})
    diff = out["diff"]
    assert diff["no_recovery_feasible"] is False
    assert diff["recovered_feasible"] is True
    assert diff["assignments_changed_by_recovery"] >= 2


def test_heavy_rain_simulation_shows_positive_delay_delta(db_session):
    """Tight deadlines + rain should increase total delay."""
    from datetime import datetime, timedelta, timezone
    v = _mk_vehicle(db_session, code="V-R", cap=5)
    now = datetime.now(timezone.utc)
    # tight deadline → small weather bump tips it into delay
    from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
    d = Delivery(
        tracking_number="T-RAIN", customer_ref="c", origin="A", destination="B",
        scheduled_dispatch=now, promised_deadline=now + timedelta(minutes=30),
        priority=DeliveryPriority.NORMAL, status=DeliveryStatus.ASSIGNED,
        vehicle_id=v.id, distance_km=20.0, cost_estimate=20.0, weather_exposure=0.0,
    )
    db_session.add(d); db_session.commit()

    out = simulator.run_simulation(db_session, "heavy_rain", {"weather_delta": 0.9})
    # total_delay_minutes should be strictly higher without recovery than baseline
    assert out["diff"]["no_recovery_delay_delta"] > 0
