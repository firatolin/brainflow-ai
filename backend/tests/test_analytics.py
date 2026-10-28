from datetime import datetime, timedelta, timezone


def _mk_vehicle(client, code="V-AN"):
    return client.post("/api/vehicles", json=dict(
        code=code, vehicle_type="van", capacity=5, status="available",
        location_zone="central", available=True, cost_per_km=1.0,
    )).json()


def _mk_delivery(client, tracking, priority="normal", vehicle_id=None):
    now = datetime.now(timezone.utc)
    return client.post("/api/deliveries", json=dict(
        tracking_number=tracking, customer_ref="c", origin="A", destination="B",
        scheduled_dispatch=now.isoformat(),
        promised_deadline=(now + timedelta(hours=4)).isoformat(),
        priority=priority, vehicle_id=vehicle_id,
        distance_km=10.0, cost_estimate=20.0, weather_exposure=0.2,
    )).json()


def test_analytics_empty(client):
    r = client.get("/api/analytics/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["measured"]["total_deliveries"] == 0
    assert body["measured"]["on_time_rate_pct"] is None
    assert body["measured"]["completion_rate_pct"] is None
    assert body["measured"]["avg_delay_minutes"] is None


def test_analytics_with_data(client):
    v = _mk_vehicle(client)
    _mk_delivery(client, "T-AN-1", vehicle_id=v["id"])
    _mk_delivery(client, "T-AN-2", priority="urgent")

    r = client.get("/api/analytics/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["measured"]["total_deliveries"] == 2
    assert len(body["estimated"]["vehicle_utilization"]) == 1
    assert len(body["trend_14d"]) == 14
    assert "note" in body["measured"]
    assert "note" in body["estimated"]


def test_analytics_reports_no_div_by_zero(client):
    # zero delivered, ensure nulls not crash
    r = client.get("/api/analytics/summary")
    assert r.status_code == 200
    b = r.json()
    assert b["measured"]["on_time_rate_pct"] is None
