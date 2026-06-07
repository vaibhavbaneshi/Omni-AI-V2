"""Sentry error tracking — optional, enabled when SENTRY_DSN is set."""

from __future__ import annotations

import logging

from app.core.app_settings import get_settings

logger = logging.getLogger(__name__)
_initialized = False


def init_sentry() -> None:
    """Initialize Sentry once at process startup."""
    global _initialized
    if _initialized:
        return

    settings = get_settings()
    dsn = (settings.SENTRY_DSN or "").strip()
    if not dsn:
        logger.debug("Sentry disabled — SENTRY_DSN not configured")
        _initialized = True
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.sentry_environment,
        release=settings.SENTRY_RELEASE or None,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=False,
    )
    logger.info("Sentry initialized environment=%s", settings.sentry_environment)
    _initialized = True
