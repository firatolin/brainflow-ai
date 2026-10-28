from datetime import datetime, timedelta, timezone


def _mk_vehicle(client, code="V1", cap=5, available=True, status="available"):
    return client.post("/api/vehicles", json=dict(
        code=code, vehicle_type="van", capacity=cap, status=status,
        location_zone="central", available=available, cost_per_km=1.0,
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


def _generate_and_pick_feasible(client, prefer_kind="minimize_delays"):
    r = client.post("/api/plans/generate")
    assert r.status_code == 200, r.text
    plans = r.json()
    for p in plans:
        if p["kind"] == prefer_kind and p["feasible"]:
            return p
    # fallback
    for p in plans:
        if p["feasible"]:
            return p
    raise AssertionError(f"No feasible plan: {[p['kind']+':'+str(p['feasible']) for p in plans]}")


def test_submit_approve_execute_flow(client):
    v = _mk_vehicle(client, code="V-FLOW", cap=10)
    _mk_delivery(client, "T-FLOW-1", vehicle_id=v["id"])
    _mk_delivery(client, "T-FLOW-2", vehicle_id=None, priority="urgent")
    plan = _generate_and_pick_feasible(client)

    # submit
    r = client.post(f"/api/plans/{plan['id']}/submit", json={"actor": "operator-a"})
    assert r.status_code == 200, r.text
    action = r.json()
    assert action["status"] == "pending_approval"
    action_id = action["id"]

    # approve
    r = client.post(f"/api/actions/{action_id}/approve", json={"reviewer": "supervisor-b", "note": "ok"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # execute
    r = client.post(f"/api/actions/{action_id}/execute", json={"reviewer": "supervisor-b"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "executed"

    # audit trail contains the events
    r = client.get(f"/api/audit-events?entity_type=operational_action&entity_id={action_id}")
    assert r.status_code == 200
    events = [e["event_type"] for e in r.json()["items"]]
    for want in ("action.submitted", "action.approved", "action.executed"):
        assert want in events, f"missing {want}; got {events}"


def test_execute_requires_approval(client):
    v = _mk_vehicle(client, code="V-NOAP", cap=10)
    _mk_delivery(client, "T-NOAP", vehicle_id=v["id"])
    plan = _generate_and_pick_feasible(client)
    action = client.post(f"/api/plans/{plan['id']}/submit", json={"actor": "op"}).json()

    r = client.post(f"/api/actions/{action['id']}/execute", json={"reviewer": "sup"})
    assert r.status_code == 409
    assert "approved" in r.text


def test_execute_is_idempotent(client):
    v = _mk_vehicle(client, code="V-IDEM", cap=10)
    _mk_delivery(client, "T-IDEM", vehicle_id=v["id"])
    _mk_delivery(client, "T-IDEM-2", vehicle_id=None, priority="urgent")
    plan = _generate_and_pick_feasible(client)
    action = client.post(f"/api/plans/{plan['id']}/submit", json={"actor": "op"}).json()
    client.post(f"/api/actions/{action['id']}/approve", json={"reviewer": "sup", "note": "ok"})

    r1 = client.post(f"/api/actions/{action['id']}/execute", json={"reviewer": "sup"})
    assert r1.status_code == 200
    r2 = client.post(f"/api/actions/{action['id']}/execute", json={"reviewer": "sup"})
    assert r2.status_code == 200
    # identical result — no re-application
    assert r2.json()["status"] == "executed"
    # audit trail: action.executed appears exactly once
    ev = client.get(f"/api/audit-events?entity_type=operational_action&entity_id={action['id']}").json()
    executed_events = [e for e in ev["items"] if e["event_type"] == "action.executed"]
    assert len(executed_events) == 1


def test_reject_flow(client):
    v = _mk_vehicle(client, code="V-REJ", cap=10)
    _mk_delivery(client, "T-REJ", vehicle_id=None, priority="urgent")
    plan = _generate_and_pick_feasible(client)
    action = client.post(f"/api/plans/{plan['id']}/submit", json={"actor": "op"}).json()

    r = client.post(f"/api/actions/{action['id']}/reject", json={"reviewer": "sup", "note": "no"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    # cannot execute after rejection
    r2 = client.post(f"/api/actions/{action['id']}/execute", json={"reviewer": "sup"})
    assert r2.status_code == 409


def test_stale_plan_blocked_on_execution(client):
    v1 = _mk_vehicle(client, code="V-STALE-A", cap=10)
    _mk_delivery(client, "T-STALE-1", vehicle_id=v1["id"])
    _mk_delivery(client, "T-STALE-2", vehicle_id=None, priority="urgent")
    plan = _generate_and_pick_feasible(client)
    action = client.post(f"/api/plans/{plan['id']}/submit", json={"actor": "op"}).json()
    client.post(f"/api/actions/{action['id']}/approve", json={"reviewer": "sup"})

    # Drift the DB: change a delivery that was in the "before" snapshot
    deliveries = client.get("/api/deliveries?page_size=100").json()["items"]
    drifted = next(d for d in deliveries if d["tracking_number"] == "T-STALE-1")
    v2 = _mk_vehicle(client, code="V-STALE-B", cap=10)
    r = client.patch(f"/api/deliveries/{drifted['id']}", json={"cost_estimate": 99.0})
    # actually drift the assignment:
    client.post(f"/api/deliveries/{drifted['id']}/assign", json={"vehicle_id": v2["id"]})

    # execute should now be blocked
    r = client.post(f"/api/actions/{action['id']}/execute", json={"reviewer": "sup"})
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert "stale" in str(detail).lower()
