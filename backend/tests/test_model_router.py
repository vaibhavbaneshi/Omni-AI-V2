"""Tests for dynamic model routing."""

from app.core.app_settings import get_settings
from app.core.llm import GroqProvider, create_llm_provider
from app.services.model_router import get_provider_for_route, resolve_model_route


def _clear_settings_cache(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


def test_routes_coding_to_deepseek_when_configured(monkeypatch):
    _clear_settings_cache(
        monkeypatch,
        MODEL_ROUTING_ENABLED="true",
        DEEPSEEK_API_KEY="sk-test",
        GROQ_API_KEY="groq-key",
    )
    route = resolve_model_route(mode="coding", query="fix this python bug")
    assert route.model_id == "deepseek-chat"
    assert route.provider == "deepseek"
    assert route.reason == "coding_task"


def test_routes_fast_query_to_lightweight_model(monkeypatch):
    _clear_settings_cache(
        monkeypatch,
        MODEL_ROUTING_ENABLED="true",
        GROQ_API_KEY="groq-key",
        DEEPSEEK_API_KEY="",
    )
    route = resolve_model_route(mode="writing", query="What is RAG?")
    assert route.model_id == "llama-fast"
    assert route.reason == "fast_query"


def test_user_selected_model_override(monkeypatch):
    _clear_settings_cache(
        monkeypatch,
        MODEL_ROUTING_ENABLED="true",
        GROQ_API_KEY="groq-key",
    )
    route = resolve_model_route(mode="coding", query="def foo():", model_id="llama-70b")
    assert route.model_id == "llama-70b"
    assert route.reason == "user_selected"


def test_routing_disabled_uses_default(monkeypatch):
    _clear_settings_cache(
        monkeypatch,
        MODEL_ROUTING_ENABLED="false",
        GROQ_API_KEY="groq-key",
        GROQ_MODEL="llama-3.3-70b-versatile",
    )
    route = resolve_model_route(mode="coding", query="def foo():")
    assert route.model_id == "llama-70b"
    assert route.reason == "routing_disabled"


def test_unknown_model_raises(monkeypatch):
    _clear_settings_cache(monkeypatch, GROQ_API_KEY="groq-key")
    try:
        resolve_model_route(model_id="not-a-model")
        assert False, "Expected LLMProviderError"
    except Exception as exc:
        assert "Unknown model id" in str(exc)


def test_create_llm_provider_with_model_override(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    provider = create_llm_provider(provider="groq", model="llama-3.1-8b-instant")
    assert isinstance(provider, GroqProvider)
    assert provider.model_name == "llama-3.1-8b-instant"


def test_get_provider_for_route(monkeypatch):
    _clear_settings_cache(
        monkeypatch,
        GROQ_API_KEY="groq-key",
        GROQ_FAST_MODEL="llama-3.1-8b-instant",
    )
    route = resolve_model_route(model_id="llama-fast")
    provider = get_provider_for_route(route)
    assert provider.name == "groq"
    assert provider.model_name == "llama-3.1-8b-instant"
