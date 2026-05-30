"""Deep health checks for production readiness."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from app.core.app_settings import get_settings
from app.core.chroma_client import get_or_create_collection
from app.core.llm import get_llm_provider
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


def check_llm(*, probe_network: bool = False) -> dict[str, Any]:
    settings = get_settings()
    try:
        provider = get_llm_provider()
        return provider.health_check(probe_network=probe_network)
    except Exception as exc:
        return {
            "status": "error",
            "provider": settings.LLM_PROVIDER,
            "detail": str(exc),
        }


def check_chroma() -> dict[str, Any]:
    settings = get_settings()
    try:
        get_or_create_collection(settings.COLLECTION_NAME)
        return {"status": "ok", "collection": settings.COLLECTION_NAME}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def run_health_checks(*, probe_llm_network: bool = False) -> dict[str, Any]:
    settings = get_settings()
    checks = {
        "database": check_database(),
        "llm": check_llm(probe_network=probe_llm_network),
        "chroma": check_chroma(),
    }

    required = {"database", "llm", "chroma"}
    if settings.LLM_PROVIDER == "groq":
        # Groq is configured locally; network probe is optional.
        overall_ok = (
            checks["database"]["status"] == "ok"
            and checks["llm"]["status"] == "ok"
            and checks["chroma"]["status"] == "ok"
        )
    else:
        overall_ok = all(checks[name].get("status") == "ok" for name in required)

    return {
        "status": "healthy" if overall_ok else "degraded",
        "provider": settings.LLM_PROVIDER,
        "checks": checks,
    }
