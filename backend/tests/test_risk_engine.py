from datetime import datetime, timedelta, timezone

import pytest

from app.models.delivery import Delivery, DeliveryPriority, DeliveryStatus
from app.models.vehicle import Vehicle
from app.services import risk_engine


def _now():
    return datetime.now(timezone.utc)


def _delivery(**over):
    now = _now()
    base = dict(
        id=1,
        tracking_number="T-1",
        customer_ref="c",
        origin="A",
        destination="B",
        scheduled_dispatch=now - timedelta(minutes=5),
        promised_deadline=now + timedelta(hours=6),
        priority=DeliveryPriority.NORMAL,
        status=DeliveryStatus.ASSIGNED,
        distance_km=10.0,
        cost_estimate=20.0,
        weather_exposure=0.0,
        updated_at=now,
    )
    base.update(over)
    d = Delivery(**base)
    return d


def _vehicle(**over):
    base = dict(id=1, code="V-1", vehicle_type="van", capacity=5,
                status="available", location_zone="central", available=True, cost_per_km=1.0)
    base.update(over)
    return Vehicle(**base)


def test_determinism_same_inputs_same_score():
    d = _delivery()
    r1 = risk_engine.assess(d, _vehicle())
    r2 = risk_engine.assess(d, _vehicle())
    assert r1.score == r2.score
    assert r1.category == r2.category


def test_low_risk_when_far_deadline_and_clean():
    d = _delivery(promised_deadline=_now() + timedelta(hours=24), weather_exposure=0.0)
    result = risk_engine.assess(d, _vehicle())
    assert result.category == "low"
    assert result.score < 30


def test_high_risk_when_deadline_passed():
    d = _delivery(promised_deadline=_now() - timedelta(hours=1), priority=DeliveryPriority.URGENT)
    result = risk_engine.assess(d, _vehicle())
    assert result.score >= 50
    assert result.category in ("high", "critical")


def test_weather_increases_score():
    now = _now()
    d_clean = _delivery(promised_deadline=now + timedelta(hours=4), weather_exposure=0.0)
    d_wet = _delivery(promised_deadline=now + timedelta(hours=4), weather_exposure=0.9)
    clean = risk_engine.assess(d_clean, _vehicle()).score
    wet = risk_engine.assess(d_wet, _vehicle()).score
    assert wet > clean


def test_confidence_lower_with_missing_vehicle():
    d = _delivery()
    conf_with = risk_engine.assess(d, _vehicle()).confidence
    conf_without = risk_engine.assess(d, None).confidence
    assert conf_without < conf_with


def test_factor_list_has_all_five_names():
    result = risk_engine.assess(_delivery(), _vehicle())
    names = {f["name"] for f in result.factors}
    assert names == {"deadline_pressure", "current_delay", "weather_exposure",
                     "priority_weight", "data_quality"}
