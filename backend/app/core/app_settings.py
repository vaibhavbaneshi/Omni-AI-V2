"""Validated application settings (env-driven, production-safe defaults)."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production"]
LLMProviderName = Literal["groq", "openai", "ollama"]
EmbeddingProviderName = Literal["local", "openai", "huggingface"]


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
    JWT_EXPIRE_MINUTES: int = 15

    LLM_PROVIDER: LLMProviderName = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"
    GROQ_REASONING_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_GEMMA_MODEL: str = "gemma2-9b-it"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # Phase 7 — automatic model selection by mode/query (explicit model param still honored).
    MODEL_ROUTING_ENABLED: bool = True

    # Optional local development provider
    OLLAMA_URL: str = "http://localhost:11434"
    MODEL_NAME: str = "llama3:latest"

    CHROMA_DB_PATH: str = "./chroma_db"
    COLLECTION_NAME: str = "omniai_docs"
    # Shared staging for RQ worker (e.g. /data/uploads on Railway volume).
    UPLOAD_STAGING_DIR: str = ""

    # local = PyTorch + SentenceTransformer (~1GB+ RAM). Use openai/huggingface on Railway.
    EMBEDDING_PROVIDER: EmbeddingProviderName = "local"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    HUGGINGFACE_API_KEY: str = ""
    HF_TOKEN: str = ""
    # Set true only on machines with >=2GB RAM and requirements-local-ml.txt installed.
    ENABLE_LOCAL_ML: bool = False
    EMBEDDING_BATCH_SIZE: int = 64
    INGEST_CHUNK_SIZE: int = 1200
    INGEST_CHUNK_OVERLAP: int = 150
    INGEST_MAX_CHUNKS: int = 400
    # Cap extracted text before chunking to limit peak RAM during ingest.
    MAX_INGEST_TEXT_CHARS: int = 600_000
    CHROMA_ADD_BATCH_SIZE: int = 128
    PRELOAD_EMBEDDING_MODEL: bool = True
    INGEST_IN_BACKGROUND: bool = True
    # Sprint 1 — durable ingestion via Redis + RQ (replaces in-process BackgroundTasks).
    INGEST_QUEUE_ENABLED: bool = True
    REDIS_URL: str = ""
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    INGEST_JOB_MAX_RETRIES: int = 3
    INGEST_JOB_RETRY_INTERVALS: str = "30,60,120"
    INGEST_JOB_RESULT_TTL_SECONDS: int = 86400
    INGEST_JOB_FAILURE_TTL_SECONDS: int = 604800
    # CrossEncoder reranker adds ~300MB RAM — disable on memory-constrained deploys.
    ENABLE_RERANKER: bool = True

    DATABASE_URL: str = ""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "omniai"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001"

    MAX_UPLOAD_BYTES: int = 20 * 1024 * 1024
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

    # Phase 6 — admin emails for platform analytics (falls back to EVAL_ADMIN_EMAILS).
    ANALYTICS_ADMIN_EMAILS: str = ""

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
    def huggingface_api_key(self) -> str:
        return self.HUGGINGFACE_API_KEY.strip() or self.HF_TOKEN.strip()

    @property
    def uses_local_ml(self) -> bool:
        return self.EMBEDDING_PROVIDER == "local" or self.ENABLE_RERANKER

    @property
    def embedding_model_label(self) -> str:
        if self.EMBEDDING_PROVIDER == "openai":
            return self.OPENAI_EMBEDDING_MODEL
        return self.EMBEDDING_MODEL

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL.strip():
            return self.REDIS_URL.strip()
        if not self.REDIS_HOST.strip():
            return ""
        password = self.REDIS_PASSWORD.strip()
        auth = f":{password}@" if password else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def ingest_job_retry_intervals(self) -> list[int]:
        parts = [part.strip() for part in self.INGEST_JOB_RETRY_INTERVALS.split(",") if part.strip()]
        return [max(1, int(part)) for part in parts] or [30, 60, 120]

    @property
    def ingest_uses_rq_queue(self) -> bool:
        return self.INGEST_QUEUE_ENABLED and bool(self.redis_url)

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
            if "*" in self.cors_origin_list:
                raise RuntimeError("CORS_ORIGINS must not include '*' in production.")
            if self.LLM_PROVIDER == "groq" and not self.GROQ_API_KEY.strip():
                raise RuntimeError("GROQ_API_KEY must be set when LLM_PROVIDER=groq in production.")
            if self.LLM_PROVIDER == "openai" and not self.OPENAI_API_KEY.strip():
                raise RuntimeError(
                    "OPENAI_API_KEY must be set when LLM_PROVIDER=openai in production."
                )
            if self.EMBEDDING_PROVIDER == "openai" and not self.OPENAI_API_KEY.strip():
                raise RuntimeError(
                    "OPENAI_API_KEY must be set when EMBEDDING_PROVIDER=openai in production."
                )
            if self.EMBEDDING_PROVIDER == "huggingface" and not self.huggingface_api_key:
                raise RuntimeError(
                    "HUGGINGFACE_API_KEY or HF_TOKEN must be set when "
                    "EMBEDDING_PROVIDER=huggingface in production."
                )
            if self.EMBEDDING_PROVIDER == "local" and not self.ENABLE_LOCAL_ML:
                raise RuntimeError(
                    "EMBEDDING_PROVIDER=local is disabled in production. "
                    "Set EMBEDDING_PROVIDER=openai or huggingface (recommended), or set "
                    "ENABLE_LOCAL_ML=true with requirements-local-ml.txt and >=2GB RAM."
                )
            if self.ENABLE_RERANKER:
                import logging

                logging.getLogger(__name__).warning(
                    "ENABLE_RERANKER=true loads CrossEncoder (~300MB). "
                    "Set ENABLE_RERANKER=false on memory-constrained deploys."
                )
            if self.INGEST_IN_BACKGROUND and self.INGEST_QUEUE_ENABLED and not self.redis_url:
                raise RuntimeError(
                    "REDIS_URL (or REDIS_HOST) must be set when INGEST_QUEUE_ENABLED=true in production."
                )


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()


def configure_langsmith_env(settings: AppSettings) -> None:
    if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGCHAIN_API_KEY)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGCHAIN_PROJECT)
