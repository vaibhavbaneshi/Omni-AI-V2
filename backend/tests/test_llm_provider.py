from app.core.llm import (
    GroqProvider,
    OllamaProvider,
    _create_stream_completion,
    get_llm,
    get_llm_provider,
    reset_llm_provider_cache,
)


def test_get_llm_provider_groq(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    reset_llm_provider_cache()

    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    provider = get_llm()
    assert isinstance(provider, GroqProvider)
    assert provider.model_name == "llama-3.3-70b-versatile"


def test_get_llm_provider_ollama(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    reset_llm_provider_cache()

    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    provider = get_llm_provider()
    assert isinstance(provider, OllamaProvider)
    assert provider.model_name == "llama3:latest"


def test_database_url_prefers_database_url(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgres://user:pass@containers-us-west-123.railway.app:5432/railway",
    )
    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.database_url.startswith("postgresql://")
    assert "railway.app" in settings.database_url
    assert settings.database_mode == "railway-postgres"


def test_create_stream_completion_falls_back_without_stream_options():
    class FakeCompletions:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if "stream_options" in kwargs:
                raise TypeError(
                    "Completions.create() got an unexpected keyword argument 'stream_options'"
                )
            return iter([])

    class FakeClient:
        def __init__(self):
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    client = FakeClient()
    stream = _create_stream_completion(
        client,
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.1,
        timeout=30,
    )
    list(stream)
    assert len(client.chat.completions.calls) == 2
    assert "stream_options" not in client.chat.completions.calls[-1]
