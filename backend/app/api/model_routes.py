"""Model catalog and routing preview endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.app_settings import get_settings
from app.core.llm import LLMProviderError
from app.services.model_router import list_routable_models, resolve_model_route

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models():
    settings = get_settings()
    return {
        "routing_enabled": settings.MODEL_ROUTING_ENABLED,
        "models": list_routable_models(available_only=False),
    }


@router.get("/route")
def preview_model_route(
    mode: str = Query(default="research"),
    query: str = Query(default=""),
    model_id: str | None = Query(default=None),
):
    try:
        route = resolve_model_route(mode=mode, query=query, model_id=model_id)
    except LLMProviderError as exc:
        return {"error": str(exc)}
    return route.to_dict()
