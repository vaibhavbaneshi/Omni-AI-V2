"""Lightweight retrieval cache — Redis-backed with in-memory fallback."""

from __future__ import annotations

from typing import Any

from app.services import redis_cache_service as cache


def cache_retrieval_result(
    *,
    query: str,
    user_id: int | None,
    workspace_id: str,
    collection_id: int | None,
    session_id: int | None = None,
    value: Any,
) -> None:
    cache.cache_retrieval_result(
        query=query,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
        value=value,
    )


def get_retrieval_cache(
    *,
    query: str,
    user_id: int | None,
    workspace_id: str,
    collection_id: int | None,
    session_id: int | None = None,
) -> Any | None:
    return cache.get_retrieval_cache(
        query=query,
        user_id=user_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        session_id=session_id,
    )


def cache_metrics() -> dict:
    return cache.cache_metrics()
