"""Validated request bodies for chat endpoints."""

from __future__ import annotations

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, ValidationError, field_validator


class ChatStreamRequest(BaseModel):
    query: str = Field(min_length=1, max_length=12_000)
    session_id: int = Field(gt=0)
    mode: str = Field(default="research", min_length=1, max_length=40)
    model: str | None = Field(default=None, max_length=80)
    workspace_id: str = Field(default="default", min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    collection_id: int | None = Field(default=None, gt=0)

    @field_validator("mode")
    @classmethod
    def normalize_mode(cls, value: str) -> str:
        allowed = {"research", "coding", "writing", "analyst", "deep-research"}
        cleaned = (value or "research").strip().lower()
        if cleaned not in allowed:
            raise ValueError(f"Unsupported mode. Allowed: {', '.join(sorted(allowed))}")
        return cleaned


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=12_000)
    session_id: int = Field(gt=0)


async def resolve_chat_stream_request(request: Request) -> ChatStreamRequest:
    """Accept JSON body or query-string parameters for backward compatibility."""
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            payload = None

        if isinstance(payload, dict) and payload:
            try:
                return ChatStreamRequest.model_validate(payload)
            except ValidationError as exc:
                raise HTTPException(status_code=422, detail=exc.errors()) from exc
        # Empty or invalid JSON body — fall through to query params (common for POST + ?query=...).

    query_params = request.query_params
    if not query_params.get("query") or not query_params.get("session_id"):
        raise HTTPException(status_code=422, detail="query and session_id are required.")

    raw: dict[str, object] = {
        "query": query_params.get("query", ""),
        "session_id": query_params.get("session_id", "0"),
        "mode": query_params.get("mode") or "research",
        "model": query_params.get("model"),
        "workspace_id": query_params.get("workspace_id") or "default",
    }
    if query_params.get("collection_id"):
        raw["collection_id"] = query_params.get("collection_id")

    try:
        return ChatStreamRequest.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
