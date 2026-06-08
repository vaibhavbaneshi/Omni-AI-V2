"""Apply Alembic migrations on application startup."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    if "pytest" in sys.modules:
        logger.debug("Skipping migrations during test run")
        return

    backend_root = Path(__file__).resolve().parents[2]
    alembic_ini = backend_root / "alembic.ini"
    if not alembic_ini.exists():
        raise RuntimeError(f"alembic.ini not found at {alembic_ini}")

    logger.info("Running database migrations (alembic upgrade head)")
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    try:
        command.upgrade(config, "head")
    except Exception as exc:
        logger.error("Database migration failed: %s", exc, exc_info=exc)
        raise RuntimeError(
            "Database migration failed. Check Railway logs for alembic errors "
            "(missing columns such as chat_sessions.is_pinned usually mean upgrade head did not run)."
        ) from exc
    logger.info("Database migrations complete")


def migration_status() -> dict[str, str | bool]:
    """Return current DB revision vs Alembic head (for /health diagnostics)."""
    if "pytest" in sys.modules:
        return {"status": "skipped", "current": "test", "head": "test", "up_to_date": True}

    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine

    from app.core.app_settings import get_settings

    backend_root = Path(__file__).resolve().parents[2]
    alembic_ini = backend_root / "alembic.ini"
    if not alembic_ini.exists():
        return {"status": "error", "detail": "alembic.ini missing", "up_to_date": False}

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head() or "unknown"

    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current = context.get_current_revision() or "none"
    except Exception as exc:
        return {
            "status": "error",
            "detail": str(exc),
            "head": head,
            "up_to_date": False,
        }

    up_to_date = current == head
    return {
        "status": "ok" if up_to_date else "pending",
        "current": current,
        "head": head,
        "up_to_date": up_to_date,
    }
