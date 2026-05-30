"""Structured startup diagnostics (no secrets, no external network probes)."""

from __future__ import annotations

import logging

from app.core.app_settings import AppSettings

logger = logging.getLogger(__name__)


def log_startup_diagnostics(settings: AppSettings) -> None:
    logger.info("Starting %s", settings.APP_NAME)
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("LLM Provider: %s", settings.LLM_PROVIDER)
    logger.info("LLM Model: %s", settings.llm_model_name)
    logger.info("Database: %s", settings.database_mode)
    logger.info("Vector Store: %s", settings.vector_store_mode)
    logger.info("Chroma path: %s", settings.CHROMA_DB_PATH)
