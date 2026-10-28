def _payload(code="VAN-T1", **overrides):
    base = dict(
        code=code,
        vehicle_type="van",
        capacity=5,
        status="available",
        location_zone="central",
        available=True,
        cost_per_km=1.2,
    )
    base.update(overrides)
    return base


def test_create_and_get_vehicle(client):
    r = client.post("/api/vehicles", json=_payload())
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["code"] == "VAN-T1"
    assert v["id"] > 0

    r2 = client.get(f"/api/vehicles/{v['id']}")
    assert r2.status_code == 200
    assert r2.json()["code"] == "VAN-T1"


def test_duplicate_vehicle_code_rejected(client):
    client.post("/api/vehicles", json=_payload("DUP-1"))
    r = client.post("/api/vehicles", json=_payload("DUP-1"))
    assert r.status_code == 409


def test_list_vehicles_pagination(client):
    for i in range(3):
        client.post("/api/vehicles", json=_payload(f"V-{i}"))
    r = client.get("/api/vehicles?page=1&page_size=2")
    body = r.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert len(body["items"]) == 2
    assert body["pages"] == 2


def test_patch_vehicle_syncs_availability(client):
    v = client.post("/api/vehicles", json=_payload("SYNC-1")).json()
    r = client.patch(f"/api/vehicles/{v['id']}", json={"status": "maintenance"})
    assert r.status_code == 200
    assert r.json()["available"] is False
