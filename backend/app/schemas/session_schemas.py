"""Validated request bodies for session endpoints."""

from __future__ import annotations

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, ValidationError


class CreateSessionRequest(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=120)
    first_message: str | None = Field(default=None, max_length=12_000)


async def resolve_create_session_request(request: Request) -> CreateSessionRequest:
    """Accept JSON body or query-string parameters for backward compatibility."""
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except Exception:
            payload = None

        if isinstance(payload, dict) and payload:
            try:
                return CreateSessionRequest.model_validate(payload)
            except ValidationError as exc:
                raise HTTPException(status_code=422, detail=exc.errors()) from exc

    query_params = request.query_params
    raw: dict[str, object] = {
        "title": query_params.get("title") or "New Chat",
        "first_message": query_params.get("first_message"),
    }

    try:
        return CreateSessionRequest.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
