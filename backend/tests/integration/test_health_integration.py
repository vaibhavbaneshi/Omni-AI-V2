"""Integration tests — health and readiness probes."""


def test_liveness_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded", "warning", "healthy"}
    assert "checks" in payload
    assert "X-Trace-Id" in response.headers


def test_readiness_health(client):
    response = client.get("/health?deep=true")
    assert response.status_code == 200
    payload = response.json()
    assert "checks" in payload
    assert "database" in payload["checks"] or "app" in payload["checks"]


def test_root_metadata(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Trace-Id")
