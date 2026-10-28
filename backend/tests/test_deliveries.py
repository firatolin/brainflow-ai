from datetime import datetime, timedelta, timezone


def _vehicle(client, code="VAN-T", capacity=5, available=True, status="available"):
    return client.post(
        "/api/vehicles",
        json=dict(
            code=code,
            vehicle_type="van",
            capacity=capacity,
            status=status,
            location_zone="central",
            available=available,
            cost_per_km=1.0,
        ),
    ).json()


def _delivery_payload(tracking="BF-T-1", vehicle_id=None, priority="normal"):
    now = datetime.now(timezone.utc)
    return dict(
        tracking_number=tracking,
        customer_ref="C-1",
        origin="A",
        destination="B",
        scheduled_dispatch=(now + timedelta(minutes=10)).isoformat(),
        promised_deadline=(now + timedelta(hours=4)).isoformat(),
        priority=priority,
        vehicle_id=vehicle_id,
        distance_km=10.0,
        cost_estimate=20.0,
        weather_exposure=0.2,
    )


def test_create_delivery_no_vehicle(client):
    r = client.post("/api/deliveries", json=_delivery_payload("BF-T-NO"))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["vehicle_id"] is None


def test_create_delivery_with_vehicle(client):
    v = _vehicle(client)
    r = client.post("/api/deliveries", json=_delivery_payload("BF-T-WV", vehicle_id=v["id"]))
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "assigned"


def test_delivery_rejects_deadline_before_dispatch(client):
    now = datetime.now(timezone.utc)
    bad = _delivery_payload("BF-BAD")
    bad["promised_deadline"] = (now - timedelta(hours=1)).isoformat()
    r = client.post("/api/deliveries", json=bad)
    assert r.status_code == 422


def test_delivery_rejects_unavailable_vehicle(client):
    v = _vehicle(client, code="MAINT", available=False, status="maintenance")
    r = client.post("/api/deliveries", json=_delivery_payload("BF-UNAV", vehicle_id=v["id"]))
    assert r.status_code == 409


def test_assign_and_status_transitions(client):
    v = _vehicle(client)
    d = client.post("/api/deliveries", json=_delivery_payload("BF-TRANS")).json()
    # assign
    r = client.post(f"/api/deliveries/{d['id']}/assign", json={"vehicle_id": v["id"]})
    assert r.status_code == 200
    assert r.json()["status"] == "assigned"

    # pending -> in_transit is invalid directly; must go assigned -> in_transit
    r = client.post(f"/api/deliveries/{d['id']}/status", json={"status": "in_transit"})
    assert r.status_code == 200
    assert r.json()["status"] == "in_transit"

    r = client.post(f"/api/deliveries/{d['id']}/status", json={"status": "delivered"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "delivered"
    assert body["actual_arrival"] is not None

    # terminal — further transitions rejected
    r = client.post(f"/api/deliveries/{d['id']}/status", json={"status": "in_transit"})
    assert r.status_code == 409


def test_capacity_enforced_on_assign(client):
    v = _vehicle(client, code="SMALL", capacity=1)
    d1 = client.post("/api/deliveries", json=_delivery_payload("BF-C1", vehicle_id=v["id"])).json()
    d2 = client.post("/api/deliveries", json=_delivery_payload("BF-C2")).json()
    r = client.post(f"/api/deliveries/{d2['id']}/assign", json={"vehicle_id": v["id"]})
    assert r.status_code == 409
    assert "capacity" in r.text.lower()


def test_history_recorded(client):
    v = _vehicle(client)
    d = client.post("/api/deliveries", json=_delivery_payload("BF-H", vehicle_id=v["id"])).json()
    client.post(f"/api/deliveries/{d['id']}/assign", json={"vehicle_id": None})
    h = client.get(f"/api/deliveries/{d['id']}/history").json()
    events = [row["event_type"] for row in h]
    assert "created" in events
    assert "unassigned" in events


def test_search_and_pagination(client):
    for i in range(5):
        client.post("/api/deliveries", json=_delivery_payload(f"BF-S-{i}"))
    r = client.get("/api/deliveries?q=BF-S&page=1&page_size=2")
    body = r.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
