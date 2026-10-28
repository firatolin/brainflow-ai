from datetime import datetime, timedelta, timezone


def test_draft_generates_with_template_fallback(client):
    now = datetime.now(timezone.utc)
    d = client.post("/api/deliveries", json=dict(
        tracking_number="T-DRAFT", customer_ref="c", origin="A", destination="B",
        scheduled_dispatch=now.isoformat(),
        promised_deadline=(now + timedelta(hours=4)).isoformat(),
        priority="urgent", vehicle_id=None,
        distance_km=10.0, cost_estimate=20.0, weather_exposure=0.2,
    )).json()
    r = client.get(f"/api/customer-drafts/{d['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["delivery_id"] == d["id"]
    assert body["source"] in ("llm", "template")
    assert body["requires_human_review"] is True
    assert body["status"] == "draft"
    assert "T-DRAFT" in body["body"]


def test_draft_404_for_missing_delivery(client):
    r = client.get("/api/customer-drafts/99999")
    assert r.status_code == 404
