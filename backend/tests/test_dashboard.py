from datetime import datetime, timedelta, timezone


def _mk_vehicle(client, code="V-DASH"):
    return client.post("/api/vehicles", json=dict(
        code=code, vehicle_type="van", capacity=5, status="available",
        location_zone="central", available=True, cost_per_km=1.0,
    )).json()


def _mk_delivery(client, tracking, priority="normal", vehicle_id=None, deadline_hours=4):
    now = datetime.now(timezone.utc)
    return client.post("/api/deliveries", json=dict(
        tracking_number=tracking, customer_ref="c", origin="A", destination="B",
        scheduled_dispatch=now.isoformat(),
        promised_deadline=(now + timedelta(hours=deadline_hours)).isoformat(),
        priority=priority, vehicle_id=vehicle_id,
        distance_km=10.0, cost_estimate=20.0, weather_exposure=0.2,
    )).json()


def test_dashboard_summary_empty(client):
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["totals"]["deliveries"] == 0
    assert body["on_time_rate_pct"] is None
    assert body["estimated_delay_exposure_minutes"] == 0.0


def test_dashboard_summary_with_data(client):
    v = _mk_vehicle(client)
    _mk_delivery(client, "T-DASH-1", vehicle_id=v["id"], priority="urgent")
    _mk_delivery(client, "T-DASH-2", priority="high")

    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["totals"]["deliveries"] == 2
    assert body["fleet"]["total"] == 1
    assert body["fleet"]["active"] == 1
    assert len(body["trend_7d"]) == 7


def test_dashboard_reflects_pending_approvals(client):
    # Create an approval action via plan submit
    v = _mk_vehicle(client, code="V-PEND")
    _mk_delivery(client, "T-PEND", vehicle_id=v["id"], priority="urgent")
    client.post("/api/plans/generate")
    plans = client.get("/api/plans?page_size=10").json()["items"]
    feasible = next((p for p in plans if p["feasible"]), None)
    if feasible:
        client.post(f"/api/plans/{feasible['id']}/submit", json={"actor": "op"})

    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["pending_approvals"] >= 1
