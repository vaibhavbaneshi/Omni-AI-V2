"""Dynamic model routing — maps task context to the best LLM provider/model."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.app_settings import get_settings
from app.core.llm import BaseLLMProvider, LLMProviderError, create_llm_provider
from app.core.model_catalog import ModelDefinition, build_model_catalog, list_model_definitions
from app.services.prompt_builder import looks_like_coding_request

REASONING_HINTS = re.compile(
    r"\b(analy(s|z)e|compare|evaluate|explain why|pros and cons|trade-?offs?|"
    r"step by step|reasoning|strategy|architecture|design|research)\b",
    re.I,
)


@dataclass(frozen=True)
class ModelRoute:
    model_id: str
    provider: str
    model_name: str
    display_name: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "id": self.model_id,
            "provider": self.provider,
            "model_name": self.model_name,
            "display_name": self.display_name,
            "routing_reason": self.reason,
        }


class ModelRouter:
    """Select provider/model based on workspace mode, query shape, and user override."""

    def __init__(self) -> None:
        self._catalog = build_model_catalog()

    def resolve(
        self,
        *,
        mode: str = "research",
        query: str = "",
        model_id: str | None = None,
    ) -> ModelRoute:
        settings = get_settings()
        cleaned_id = (model_id or "").strip().lower()

        if cleaned_id and cleaned_id not in ("auto", ""):
            definition = self._catalog.get(cleaned_id)
            if definition and definition.id != "auto":
                if not definition.is_available():
                    raise LLMProviderError(
                        f"Model '{definition.name}' is not configured on the server."
                    )
                return ModelRoute(
                    model_id=definition.id,
                    provider=definition.provider,
                    model_name=definition.model_name,
                    display_name=definition.name,
                    reason="user_selected",
                )
            raise LLMProviderError(f"Unknown model id '{cleaned_id}'.")

        if not settings.MODEL_ROUTING_ENABLED:
            default = self._catalog["llama-70b"]
            return ModelRoute(
                model_id=default.id,
                provider=default.provider,
                model_name=default.model_name,
                display_name=default.name,
                reason="routing_disabled",
            )

        if mode == "coding" or looks_like_coding_request(query, mode):
            route = self._route_if_available("deepseek-chat", reason="coding_task")
            if route:
                return route

        if mode in {"research", "analyst"} or self._looks_like_reasoning(query):
            route = self._route_if_available("llama-70b", reason=f"{mode}_mode")
            if route:
                return route

        if self._is_fast_query(query):
            route = self._route_if_available("llama-fast", reason="fast_query")
            if route:
                return route

        route = self._route_if_available("llama-70b", reason="general_chat")
        if route:
            return route

        # Last-resort fallback to global default provider.
        default = self._catalog["llama-70b"]
        return ModelRoute(
            model_id=default.id,
            provider=settings.LLM_PROVIDER,
            model_name=settings.llm_model_name,
            display_name=default.name,
            reason="fallback_default",
        )

    def _route_if_available(self, model_id: str, *, reason: str) -> ModelRoute | None:
        definition = self._catalog.get(model_id)
        if not definition or not definition.is_available():
            return None
        return ModelRoute(
            model_id=definition.id,
            provider=definition.provider,
            model_name=definition.model_name,
            display_name=definition.name,
            reason=reason,
        )

    @staticmethod
    def _is_fast_query(query: str) -> bool:
        text = (query or "").strip()
        return 0 < len(text) <= 80 and text.count(" ") < 12

    @staticmethod
    def _looks_like_reasoning(query: str) -> bool:
        return bool(REASONING_HINTS.search(query or ""))


def get_model_router() -> ModelRouter:
    return ModelRouter()


def resolve_model_route(
    *,
    mode: str = "research",
    query: str = "",
    model_id: str | None = None,
) -> ModelRoute:
    return get_model_router().resolve(mode=mode, query=query, model_id=model_id)


def get_provider_for_route(route: ModelRoute) -> BaseLLMProvider:
    if route.provider == "router":
        raise LLMProviderError("Cannot instantiate router pseudo-provider.")
    return create_llm_provider(provider=route.provider, model=route.model_name)


def list_routable_models(*, available_only: bool = True) -> list[dict]:
    return [model.to_dict() for model in list_model_definitions(available_only=available_only)]
