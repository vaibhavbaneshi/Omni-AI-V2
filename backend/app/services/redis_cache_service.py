"""Redis-backed cache with in-memory fallback and hit/miss metrics."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from app.core.app_settings import get_settings

logger = logging.getLogger(__name__)

_MEMORY: dict[str, tuple[float, str]] = {}
_METRICS = {"hits": 0, "misses": 0, "errors": 0}
_DEFAULT_TTL = 300


def _redis_client():
    settings = get_settings()
    if not settings.redis_url:
        return None
    try:
        import redis

        return redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        logger.exception("Redis cache client unavailable")
        return None


def _key(namespace: str, *parts: str | int | None) -> str:
    raw = "|".join(str(part) for part in (namespace, *parts))
    return f"omniai:cache:{hashlib.sha256(raw.encode()).hexdigest()}"


def get_cached(namespace: str, *parts: str | int | None) -> Any | None:
    cache_key = _key(namespace, *parts)
    client = _redis_client()
    if client:
        try:
            payload = client.get(cache_key)
            if payload is not None:
                _METRICS["hits"] += 1
                return json.loads(payload)
        except Exception:
            _METRICS["errors"] += 1
            logger.exception("Redis cache get failed key=%s", cache_key)

    item = _MEMORY.get(cache_key)
    if item and item[0] >= time.time():
        _METRICS["hits"] += 1
        return json.loads(item[1])

    _METRICS["misses"] += 1
    return None


def set_cached(
    namespace: str,
    *parts: str | int | None,
    value: Any,
    ttl_seconds: int = _DEFAULT_TTL,
) -> None:
    cache_key = _key(namespace, *parts)
    payload = json.dumps(value, default=str)
    client = _redis_client()
    if client:
        try:
            client.setex(cache_key, ttl_seconds, payload)
            return
        except Exception:
            _METRICS["errors"] += 1
            logger.exception("Redis cache set failed key=%s", cache_key)
    _MEMORY[cache_key] = (time.time() + ttl_seconds, payload)


def cache_metrics() -> dict[str, int]:
    total = _METRICS["hits"] + _METRICS["misses"]
    hit_rate = round((_METRICS["hits"] / total) * 100, 2) if total else 0.0
    return {**_METRICS, "total": total, "hit_rate_pct": hit_rate}


def cache_retrieval_result(
    *,
    query: str,
    user_id: int | None,
    workspace_id: str,
    collection_id: int | None,
    session_id: int | None = None,
    value: Any,
    ttl_seconds: int = _DEFAULT_TTL,
) -> None:
    set_cached(
        "retrieval",
        query,
        user_id,
        workspace_id,
        collection_id,
        session_id,
        value=value,
        ttl_seconds=ttl_seconds,
    )


def get_retrieval_cache(
    *,
    query: str,
    user_id: int | None,
    workspace_id: str,
    collection_id: int | None,
    session_id: int | None = None,
) -> Any | None:
    return get_cached("retrieval", query, user_id, workspace_id, collection_id, session_id)


def cache_embedding(text: str, vector: list[float], ttl_seconds: int = 3600) -> None:
    set_cached("embedding", text, value=vector, ttl_seconds=ttl_seconds)


def get_embedding_cache(text: str) -> list[float] | None:
    return get_cached("embedding", text)


def cache_query_result(namespace: str, query: str, user_id: int | None, value: Any, ttl_seconds: int = 600) -> None:
    set_cached(namespace, query, user_id, value=value, ttl_seconds=ttl_seconds)


def get_query_cache(namespace: str, query: str, user_id: int | None) -> Any | None:
    return get_cached(namespace, query, user_id)
