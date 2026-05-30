"""Validated application settings (env-driven, production-safe defaults)."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production"]
LLMProviderName = Literal["groq", "openai", "ollama"]


def _normalize_database_url(url: str) -> str:
    """Railway and Heroku often provide postgres:// — SQLAlchemy expects postgresql://."""
    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = "postgresql://" + normalized[len("postgres://") :]
    return normalized


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "OmniAI"
    ENVIRONMENT: Environment = "development"
    API_PUBLIC_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    JWT_SECRET_KEY: str = Field(
        default="dev-only-change-me-before-production",
        validation_alias="JWT_SECRET_KEY",
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    LLM_PROVIDER: LLMProviderName = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Optional local development provider
    OLLAMA_URL: str = "http://localhost:11434"
    MODEL_NAME: str = "llama3:latest"

    CHROMA_DB_PATH: str = "./chroma_db"
    COLLECTION_NAME: str = "omniai_docs"

    DATABASE_URL: str = ""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "omniai"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001"

    MAX_UPLOAD_BYTES: int = 15 * 1024 * 1024
    RATE_LIMIT_PER_MINUTE: int = 120
    MAX_QUERY_CHARS: int = 12_000

    # Conversation memory windowing (Phase 3).
    CHAT_HISTORY_MESSAGE_LIMIT: int = 8
    CONVERSATION_SUMMARY_MIN_MESSAGES: int = 6
    CONVERSATION_SUMMARY_MAX_CHARS: int = 4000

    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "OmniAI"

    # Persist API/model/token metrics to PostgreSQL (Phase 1 observability).
    ENABLE_USAGE_TRACKING: bool = True

    # Phase 4 — comma-separated admin emails allowed to POST /evaluation/run in production.
    EVAL_ADMIN_EMAILS: str = ""

    ENABLE_DEEP_RESEARCH: bool = False
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    TAVILY_API_KEY: str = ""
    SERPER_API_KEY: str = ""
    WEB_SEARCH_PROVIDER: str = "tavily"

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def normalize_env(cls, value: str) -> str:
        return (value or "development").strip().lower()

    @field_validator("LLM_PROVIDER", mode="before")
    @classmethod
    def normalize_llm_provider(cls, value: str) -> str:
        return (value or "groq").strip().lower()

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL.strip():
            return _normalize_database_url(self.DATABASE_URL)
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_mode(self) -> str:
        if self.DATABASE_URL.strip():
            return "railway-postgres"
        return "local-postgres"

    @property
    def vector_store_mode(self) -> str:
        return "chroma"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def llm_model_name(self) -> str:
        if self.LLM_PROVIDER == "groq":
            return self.GROQ_MODEL
        if self.LLM_PROVIDER == "openai":
            return self.OPENAI_MODEL
        return self.MODEL_NAME

    def validate_for_runtime(self) -> None:
        if self.ENVIRONMENT == "production":
            if self.JWT_SECRET_KEY.startswith("dev-only"):
                raise RuntimeError(
                    "JWT_SECRET_KEY must be set to a strong secret in production."
                )
            if len(self.JWT_SECRET_KEY) < 32:
                raise RuntimeError("JWT_SECRET_KEY should be at least 32 characters in production.")
            if self.LLM_PROVIDER == "groq" and not self.GROQ_API_KEY.strip():
                raise RuntimeError("GROQ_API_KEY must be set when LLM_PROVIDER=groq in production.")
            if self.LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY.strip():
                raise RuntimeError(
                    "OPENAI_API_KEY must be set when LLM_PROVIDER=openai in production."
                )


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()


def configure_langsmith_env(settings: AppSettings) -> None:
    if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGCHAIN_API_KEY)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGCHAIN_PROJECT)
