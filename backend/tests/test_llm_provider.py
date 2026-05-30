from app.core.llm import GroqProvider, OllamaProvider, get_llm_provider, reset_llm_provider_cache


def test_get_llm_provider_groq(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    reset_llm_provider_cache()

    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    provider = get_llm_provider()
    assert isinstance(provider, GroqProvider)
    assert provider.model_name == "llama-3.3-70b-versatile"


def test_get_llm_provider_ollama(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    reset_llm_provider_cache()

    from app.core.app_settings import get_settings

    get_settings.cache_clear()
    provider = get_llm_provider()
    assert isinstance(provider, OllamaProvider)
