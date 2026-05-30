"""Catalog of routable models and provider metadata."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.app_settings import get_settings


@dataclass(frozen=True)
class ModelDefinition:
    id: str
    name: str
    provider: str
    model_name: str
    description: str
    roles: tuple[str, ...] = ()
    badge: str | None = None

    def is_available(self) -> bool:
        settings = get_settings()
        if self.provider == "groq":
            return bool(settings.GROQ_API_KEY.strip())
        if self.provider == "deepseek":
            return bool(settings.DEEPSEEK_API_KEY.strip())
        if self.provider == "openai":
            return bool(settings.OPENAI_API_KEY.strip())
        if self.provider == "ollama":
            return bool(settings.OLLAMA_URL.strip())
        return False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "model_name": self.model_name,
            "description": self.description,
            "roles": list(self.roles),
            "badge": self.badge,
            "available": self.is_available(),
        }


def build_model_catalog() -> dict[str, ModelDefinition]:
    settings = get_settings()
    return {
        "auto": ModelDefinition(
            id="auto",
            name="Auto Route",
            provider="router",
            model_name="auto",
            description="Automatically pick the best model for your task.",
            roles=("auto",),
            badge="Smart",
        ),
        "llama-70b": ModelDefinition(
            id="llama-70b",
            name="Llama 3.3 70B",
            provider="groq",
            model_name=settings.GROQ_REASONING_MODEL,
            description="Best for reasoning, research, and general chat.",
            roles=("general", "reasoning", "research"),
            badge="Default",
        ),
        "llama-fast": ModelDefinition(
            id="llama-fast",
            name="Llama 3.1 8B",
            provider="groq",
            model_name=settings.GROQ_FAST_MODEL,
            description="Low-latency responses for quick questions.",
            roles=("fast", "general"),
        ),
        "deepseek-chat": ModelDefinition(
            id="deepseek-chat",
            name="DeepSeek Chat",
            provider="deepseek",
            model_name=settings.DEEPSEEK_MODEL,
            description="Optimized for coding, debugging, and technical tasks.",
            roles=("coding",),
            badge="Code",
        ),
        "gemma-9b": ModelDefinition(
            id="gemma-9b",
            name="Gemma 2 9B",
            provider="groq",
            model_name=settings.GROQ_GEMMA_MODEL,
            description="Lightweight Google Gemma model via Groq.",
            roles=("fast", "general"),
        ),
    }


def list_model_definitions(*, available_only: bool = False) -> list[ModelDefinition]:
    catalog = build_model_catalog()
    models = list(catalog.values())
    if available_only:
        return [model for model in models if model.id == "auto" or model.is_available()]
    return models
