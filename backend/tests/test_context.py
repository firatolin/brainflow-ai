def test_weather_endpoint_returns_snapshot(client):
    r = client.get("/api/context/weather?zone=east")
    assert r.status_code == 200
    body = r.json()
    assert body["zone"] == "east"
    assert body["source"] in ("open-meteo", "demo")
    assert 0.0 <= body["severity"] <= 1.0


def test_weather_unknown_zone_falls_back_to_demo(client):
    r = client.get("/api/context/weather?zone=atlantis")
    assert r.status_code == 200
    assert r.json()["source"] == "demo"


def test_holidays_endpoint(client):
    r = client.get("/api/context/holidays?country=ET")
    assert r.status_code == 200
    body = r.json()
    assert body["country"] == "ET"
    assert isinstance(body["holidays"], list)
