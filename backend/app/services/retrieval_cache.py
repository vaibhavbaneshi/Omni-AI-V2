"""Lightweight in-memory retrieval cache with TTL."""

from __future__ import annotations

import hashlib
import time
from typing import Any

_CACHE: dict[str, tuple[float, Any]] = {}
_DEFAULT_TTL_SECONDS = 300


def _cache_key(*parts: str | int | None) -> str:
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached(key: str) -> Any | None:
    item = _CACHE.get(key)
    if not item:
        return None
    expires_at, value = item
    if expires_at < time.time():
        _CACHE.pop(key, None)
        return None
    return value


def set_cached(key: str, value: Any, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
    _CACHE[key] = (time.time() + ttl_seconds, value)


def cache_retrieval_result(
    *,
    query: str,
    user_id: int | None,
    workspace_id: str,
    collection_id: int | None,
    session_id: int | None = None,
    value: Any,
) -> None:
    key = _cache_key("retrieval", query, user_id, workspace_id, collection_id, session_id)
    set_cached(key, value)


def get_retrieval_cache(
    *,
    query: str,
    user_id: int | None,
    workspace_id: str,
    collection_id: int | None,
    session_id: int | None = None,
) -> Any | None:
    key = _cache_key("retrieval", query, user_id, workspace_id, collection_id, session_id)
    return get_cached(key)
