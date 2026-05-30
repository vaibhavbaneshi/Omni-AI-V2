"""Shared ChromaDB client factory with telemetry disabled globally."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Must be set before chromadb/posthog import.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "FALSE")


def _silence_chroma_telemetry() -> None:
    """Disable Chroma product telemetry (posthog API mismatch in chromadb 0.5.x)."""
    try:
        import posthog

        posthog.disabled = True
        posthog.capture = lambda *args, **kwargs: None  # noqa: E731
    except ImportError:
        pass


_silence_chroma_telemetry()

import chromadb
from chromadb.config import Settings

from app.core.app_settings import get_settings

if TYPE_CHECKING:
    from chromadb import Collection

_clients: dict[str, chromadb.PersistentClient] = {}

_CHROMA_SETTINGS = Settings(anonymized_telemetry=False)


def get_chroma_client(path: str | None = None) -> chromadb.PersistentClient:
    resolved_path = path or get_settings().CHROMA_DB_PATH
    if resolved_path not in _clients:
        _clients[resolved_path] = chromadb.PersistentClient(
            path=resolved_path,
            settings=_CHROMA_SETTINGS,
        )
        logger.debug("Created Chroma PersistentClient at %s (telemetry disabled)", resolved_path)
    return _clients[resolved_path]


def get_or_create_collection(name: str | None = None) -> "Collection":
    settings = get_settings()
    collection_name = name or settings.COLLECTION_NAME
    client = get_chroma_client(settings.CHROMA_DB_PATH)
    return client.get_or_create_collection(name=collection_name)


def get_collection(name: str | None = None) -> "Collection":
    settings = get_settings()
    collection_name = name or settings.COLLECTION_NAME
    client = get_chroma_client(settings.CHROMA_DB_PATH)
    return client.get_collection(name=collection_name)
