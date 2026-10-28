from datetime import datetime, timedelta, timezone


def _mk_vehicle(client, code="V1"):
    return client.post("/api/vehicles", json=dict(
        code=code, vehicle_type="van", capacity=5, status="available",
        location_zone="central", available=True, cost_per_km=1.0,
    )).json()


def _mk_delivery(client, tracking, vehicle_id=None, priority="normal"):
    now = datetime.now(timezone.utc)
    return client.post("/api/deliveries", json=dict(
        tracking_number=tracking, customer_ref="c", origin="A", destination="B",
        scheduled_dispatch=now.isoformat(),
        promised_deadline=(now + timedelta(hours=4)).isoformat(),
        priority=priority, vehicle_id=vehicle_id,
        distance_km=10.0, cost_estimate=20.0, weather_exposure=0.1,
    )).json()


def test_generate_plans_returns_three(client):
    v = _mk_vehicle(client)
    _mk_delivery(client, "T-1", vehicle_id=v["id"])
    _mk_delivery(client, "T-2", vehicle_id=None, priority="urgent")
    r = client.post("/api/plans/generate")
    assert r.status_code == 200
    body = r.json()
    kinds = {p["kind"] for p in body}
    assert kinds == {"baseline", "minimize_delays", "balanced"}


def test_plans_list_and_get(client):
    v = _mk_vehicle(client, code="V-L")
    _mk_delivery(client, "T-L", vehicle_id=v["id"])
    client.post("/api/plans/generate")
    r = client.get("/api/plans?page_size=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 3

    pid = body["items"][0]["id"]
    r2 = client.get(f"/api/plans/{pid}")
    assert r2.status_code == 200
    assert "items" in r2.json()


def test_simulation_via_api_persists(client):
    v = _mk_vehicle(client, code="V-SIM")
    _mk_delivery(client, "T-SIM", vehicle_id=v["id"])
    r = client.post("/api/simulations", json={
        "scenario": "vehicle_unavailable",
        "params": {"vehicle_id": v["id"]},
    })
    assert r.status_code == 200, r.text
    body = r.json()
    sim_id = body["id"]
    r2 = client.get(f"/api/simulations/{sim_id}")
    assert r2.status_code == 200
