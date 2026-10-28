
from datetime import datetime, timedelta, timezone


def _mk_vehicle(client, code="V1"):
    return client.post("/api/vehicles", json=dict(
        code=code, vehicle_type="van", capacity=5, status="available",
        location_zone="central", available=True, cost_per_km=1.0,
    )).json()


def _mk_delivery(client, tracking, priority="normal", vehicle_id=None, risk_score=None):
    now = datetime.now(timezone.utc)
    d = client.post("/api/deliveries", json=dict(
        tracking_number=tracking, customer_ref="c", origin="A", destination="B",
        scheduled_dispatch=now.isoformat(),
        promised_deadline=(now + timedelta(hours=4)).isoformat(),
        priority=priority, vehicle_id=vehicle_id,
        distance_km=10.0, cost_estimate=20.0, weather_exposure=0.2,
    )).json()
    return d


def test_copilot_fallback_when_no_llm(client):
    v = _mk_vehicle(client, code="V-COP")
    _mk_delivery(client, "T-COP-1", vehicle_id=v["id"])

    r = client.post("/api/copilot/query", json={"question": "Summarize the current situation"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "fallback"
    assert "active deliveries" in body["answer"].lower() or "situation" in body["answer"].lower()


def test_copilot_at_risk_routing(client):
    v = _mk_vehicle(client, code="V-RISK")
    _mk_delivery(client, "T-RISK", vehicle_id=v["id"])
    client.post("/api/scan-runs")  # populate risk scores

    r = client.post("/api/copilot/query", json={"question": "Which deliveries are most likely to be late?"})
    assert r.status_code == 200
    assert r.json()["tool_used"] == "deliveries_at_risk"


def test_copilot_priority_routing(client):
    _mk_delivery(client, "T-PR-1", priority="urgent")
    r = client.post("/api/copilot/query", json={"question": "Which deliveries should be prioritized?"})
    assert r.status_code == 200
    assert r.json()["tool_used"] == "priority_deliveries"


def test_health_reports_ai_provider(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert "ai" in body
    assert body["ai"]["provider"] in ("fallback", "gemini")
