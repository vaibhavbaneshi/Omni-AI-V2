"""Shared ChromaDB client factory with telemetry disabled."""

from __future__ import annotations

import os

# Must be set before chromadb import to suppress posthog telemetry errors.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.app_settings import get_settings

_clients: dict[str, chromadb.PersistentClient] = {}


def get_chroma_client(path: str | None = None) -> chromadb.PersistentClient:
    resolved_path = path or get_settings().CHROMA_DB_PATH
    if resolved_path not in _clients:
        _clients[resolved_path] = chromadb.PersistentClient(
            path=resolved_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _clients[resolved_path]


def get_or_create_collection(name: str | None = None):
    settings = get_settings()
    collection_name = name or settings.COLLECTION_NAME
    client = get_chroma_client(settings.CHROMA_DB_PATH)
    return client.get_or_create_collection(name=collection_name)
