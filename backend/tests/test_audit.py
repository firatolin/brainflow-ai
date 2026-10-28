def test_audit_events_paginated_and_searchable(client):
    # create an event by submitting a plan
    v = client.post("/api/vehicles", json=dict(
        code="V-AUD", vehicle_type="van", capacity=5, status="available",
        location_zone="central", available=True, cost_per_km=1.0,
    )).json()
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    client.post("/api/deliveries", json=dict(
        tracking_number="T-AUD", customer_ref="c", origin="A", destination="B",
        scheduled_dispatch=now.isoformat(),
        promised_deadline=(now + timedelta(hours=4)).isoformat(),
        priority="urgent", vehicle_id=None,
        distance_km=10.0, cost_estimate=20.0, weather_exposure=0.1,
    ))
    client.post("/api/plans/generate")
    plans = client.get("/api/plans?page_size=10").json()["items"]
    feasible = next((p for p in plans if p["feasible"]), None)
    if feasible:
        client.post(f"/api/plans/{feasible['id']}/submit", json={"actor": "tester"})

    r = client.get("/api/audit-events?page_size=5")
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # searchable by actor
    r = client.get("/api/audit-events?q=tester")
    assert r.status_code == 200
