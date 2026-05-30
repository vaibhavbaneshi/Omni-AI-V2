"""Health checks — non-fatal at startup, optional deep probes via /health."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from app.core.app_settings import get_settings
from app.core.chroma_client import get_or_create_collection
from app.core.llm import get_llm
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def check_llm_config() -> dict[str, Any]:
    """Config-only LLM check — never contacts Ollama or external APIs."""
    settings = get_settings()
    provider = settings.LLM_PROVIDER

    if provider == "groq":
        if not settings.GROQ_API_KEY.strip():
            return {
                "status": "warning",
                "provider": provider,
                "detail": "GROQ_API_KEY is not configured",
            }
        return {
            "status": "ok",
            "provider": provider,
            "model": settings.GROQ_MODEL,
            "configured": True,
        }

    if provider == "openai":
        if not settings.OPENAI_API_KEY.strip():
            return {
                "status": "warning",
                "provider": provider,
                "detail": "OPENAI_API_KEY is not configured",
            }
        return {
            "status": "ok",
            "provider": provider,
            "model": settings.OPENAI_MODEL,
            "configured": True,
        }

    if provider == "ollama":
        return {
            "status": "ok",
            "provider": provider,
            "model": settings.MODEL_NAME,
            "configured": True,
        }

    return {
        "status": "warning",
        "provider": provider,
        "detail": f"Unsupported LLM_PROVIDER '{provider}'",
    }


def check_database(*, probe: bool = True) -> dict[str, Any]:
    if not probe:
        settings = get_settings()
        return {"status": "ok", "mode": settings.database_mode, "configured": True}

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ok", "mode": get_settings().database_mode}
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return {"status": "warning", "detail": str(exc)}


def check_chroma_config() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "mode": settings.vector_store_mode,
        "path": settings.CHROMA_DB_PATH,
        "collection": settings.COLLECTION_NAME,
        "configured": True,
    }


def check_chroma(*, probe: bool = True) -> dict[str, Any]:
    if not probe:
        return check_chroma_config()

    settings = get_settings()
    try:
        get_or_create_collection(settings.COLLECTION_NAME)
        return {
            "status": "ok",
            "mode": settings.vector_store_mode,
            "collection": settings.COLLECTION_NAME,
        }
    except Exception as exc:
        logger.warning("Chroma health check failed: %s", exc)
        return {"status": "warning", "detail": str(exc)}


def check_llm(*, probe_network: bool = False) -> dict[str, Any]:
    if not probe_network:
        return check_llm_config()

    settings = get_settings()
    try:
        provider = get_llm()
        return provider.health_check(probe_network=True)
    except Exception as exc:
        logger.warning("LLM network health check failed: %s", exc)
        return {
            "status": "warning",
            "provider": settings.LLM_PROVIDER,
            "detail": str(exc),
        }


def run_startup_checks() -> dict[str, Any]:
    """Non-fatal startup diagnostics — logs warnings, never blocks boot."""
    settings = get_settings()
    checks = {
        "database": check_database(probe=False),
        "llm": check_llm_config(),
        "chroma": check_chroma_config(),
    }

    for name, result in checks.items():
        status = result.get("status", "unknown")
        if status != "ok":
            logger.warning("Startup check '%s' not ready: %s", name, result.get("detail", result))
        else:
            logger.info("Startup check '%s': ok", name)

    return {
        "status": "started",
        "environment": settings.ENVIRONMENT,
        "provider": settings.LLM_PROVIDER,
        "database_mode": settings.database_mode,
        "vector_store": settings.vector_store_mode,
        "checks": checks,
    }


def run_health_checks(*, probe_llm_network: bool = False, probe_dependencies: bool = True) -> dict[str, Any]:
    settings = get_settings()
    checks = {
        "database": check_database(probe=probe_dependencies),
        "llm": check_llm(probe_network=probe_llm_network),
        "chroma": check_chroma(probe=probe_dependencies),
    }

    statuses = [item.get("status") for item in checks.values()]
    if all(status == "ok" for status in statuses):
        overall = "healthy"
    elif any(status == "error" for status in statuses):
        overall = "degraded"
    else:
        overall = "degraded"

    return {
        "status": overall,
        "environment": settings.ENVIRONMENT,
        "provider": settings.LLM_PROVIDER,
        "database_mode": settings.database_mode,
        "vector_store": settings.vector_store_mode,
        "checks": checks,
    }
