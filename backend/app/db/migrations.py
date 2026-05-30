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
        logger.warning("alembic.ini not found at %s; skipping migrations", alembic_ini)
        return

    logger.info("Running database migrations (alembic upgrade head)")
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    command.upgrade(config, "head")
    logger.info("Database migrations complete")
