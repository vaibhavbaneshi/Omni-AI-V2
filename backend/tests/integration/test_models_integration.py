"""Integration tests — model catalog endpoints."""

from app.core.app_settings import get_settings


def test_list_models(auth_client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    get_settings.cache_clear()

    response = auth_client.get("/models", headers=auth_client.auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert "models" in payload
    assert payload["routing_enabled"] is True
    ids = {model["id"] for model in payload["models"]}
    assert "auto" in ids
    assert "llama-70b" in ids


def test_preview_model_route(auth_client, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("MODEL_ROUTING_ENABLED", "true")
    get_settings.cache_clear()

    response = auth_client.get(
        "/models/route?mode=coding&query=fix+this+python+bug+with+detailed+explanation",
        headers=auth_client.auth_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "deepseek-chat"
