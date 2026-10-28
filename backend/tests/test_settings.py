def test_settings_endpoint(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["admin"]["username"] == "admin"
    assert body["admin"]["display_name"] == "Admin"
    assert body["auth_mode"] == "demo_no_auth"
    assert "note" in body
