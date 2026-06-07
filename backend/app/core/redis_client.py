"""Shared Redis connection for RQ ingestion workers."""

from __future__ import annotations

import logging

import redis

from app.core.app_settings import get_settings

logger = logging.getLogger(__name__)

_connection: redis.Redis | None = None


def get_redis_connection() -> redis.Redis:
    global _connection
    if _connection is None:
        settings = get_settings()
        url = settings.redis_url
        if not url:
            raise RuntimeError(
                "REDIS_URL is not configured. Set REDIS_URL or REDIS_HOST for ingestion queue."
            )
        _connection = redis.from_url(url, decode_responses=False)
        logger.debug("Redis connection established for ingestion queue")
    return _connection


def reset_redis_connection() -> None:
    """Close cached connection (tests / worker reload)."""
    global _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
    _connection = None


def try_get_redis_connection() -> redis.Redis | None:
    """Return Redis client when configured; None if unavailable."""
    try:
        return get_redis_connection()
    except Exception:
        return None
