"""Backward-compatible settings facade over validated AppSettings."""

from app.core.app_settings import get_settings

_settings = get_settings()


class Settings:
    APP_NAME = _settings.APP_NAME
    OLLAMA_URL = _settings.ollama_generate_url
    MODEL_NAME = _settings.resolved_model_name
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


settings = Settings()
