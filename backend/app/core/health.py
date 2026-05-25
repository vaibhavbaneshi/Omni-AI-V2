"""Deep health checks for production readiness."""

from __future__ import annotations

import logging
from typing import Any

import requests
from sqlalchemy import text

from app.core.app_settings import get_settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def check_database() -> dict[str, Any]:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


def check_ollama() -> dict[str, Any]:
    settings = get_settings()
    base = settings.ollama_generate_url.rsplit("/api/", 1)[0]
    try:
        response = requests.get(f"{base}/api/tags", timeout=3)
        response.raise_for_status()
        models = [m.get("name") for m in response.json().get("models", [])]
        resolved = settings.resolved_model_name
        return {
            "status": "ok",
            "model": resolved,
            "model_available": resolved in models if models else True,
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def check_chroma() -> dict[str, Any]:
    settings = get_settings()
    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        client.get_or_create_collection(name=settings.COLLECTION_NAME)
        return {"status": "ok", "collection": settings.COLLECTION_NAME}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def run_health_checks() -> dict[str, Any]:
    checks = {
        "database": check_database(),
        "ollama": check_ollama(),
        "chroma": check_chroma(),
    }
    overall = (
        "healthy"
        if all(item.get("status") == "ok" for item in checks.values())
        else "degraded"
    )
    return {"status": overall, "checks": checks}
