"""Backward-compatible settings facade over validated AppSettings."""

from app.core.app_settings import get_settings

_settings = get_settings()


class Settings:
    """Lazy facade — no Ollama network calls at import time."""

    APP_NAME = _settings.APP_NAME
    CHROMA_DB_PATH = _settings.CHROMA_DB_PATH
    COLLECTION_NAME = _settings.COLLECTION_NAME
    TAVILY_API_KEY = _settings.TAVILY_API_KEY
    SERPER_API_KEY = _settings.SERPER_API_KEY
    WEB_SEARCH_PROVIDER = _settings.WEB_SEARCH_PROVIDER
    POSTGRES_HOST = _settings.POSTGRES_HOST
    POSTGRES_PORT = _settings.POSTGRES_PORT
    POSTGRES_DB = _settings.POSTGRES_DB
    POSTGRES_USER = _settings.POSTGRES_USER
    POSTGRES_PASSWORD = _settings.POSTGRES_PASSWORD
    LLM_PROVIDER = _settings.LLM_PROVIDER

    @property
    def MODEL_NAME(self) -> str:
        return get_settings().llm_model_name

    @property
    def database_url(self) -> str:
        return get_settings().database_url

    @property
    def OLLAMA_URL(self) -> str:
        # Kept for backward compatibility in legacy code paths only.
        return get_settings().OLLAMA_URL


settings = Settings()
