import pytest


def _login(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "BrainFlow@2026"})
    assert r.status_code == 200, r.text
    return r


@pytest.mark.no_auth
def test_login_success(client):
    r = _login(client)
    body = r.json()
    assert body["username"] == "admin"
    assert body["display_name"] == "Admin"
    assert client.cookies.get("brainflow_session")


@pytest.mark.no_auth
def test_login_failure(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.no_auth
def test_auth_status_when_logged_out(client):
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    assert r.json()["authenticated"] is False


def test_auth_status_when_logged_in(client):
    # autouse login already ran
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is True
    assert body["user"]["username"] == "admin"


def test_logout_clears_session(client):
    # already logged in
    client.post("/api/auth/logout")
    client.cookies.clear()
    r = client.get("/api/auth/status")
    assert r.json()["authenticated"] is False


@pytest.mark.no_auth
def test_mutating_endpoints_require_auth(client):
    r = client.post("/api/vehicles", json=dict(
        code="V-NOAUTH", vehicle_type="van", capacity=5, status="available",
        location_zone="central", available=True, cost_per_km=1.0,
    ))
    assert r.status_code == 401

    r = client.post("/api/incidents/scan")
    assert r.status_code == 401

    r = client.post("/api/plans/generate")
    assert r.status_code == 401


@pytest.mark.no_auth
def test_read_endpoints_public(client):
    for path in ("/api/health", "/api/dashboard/summary", "/api/analytics/summary"):
        r = client.get(path)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
