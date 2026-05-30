"""Shared admin access checks for analytics and evaluation endpoints."""

from __future__ import annotations

from app.core.app_settings import AppSettings, get_settings
from app.models.user import User


def get_admin_emails(settings: AppSettings | None = None) -> list[str]:
    settings = settings or get_settings()
    raw = settings.ANALYTICS_ADMIN_EMAILS or settings.EVAL_ADMIN_EMAILS
    return [email.strip().lower() for email in raw.split(",") if email.strip()]


def user_has_admin_access(user: User, settings: AppSettings | None = None) -> bool:
    settings = settings or get_settings()
    allowed = get_admin_emails(settings)
    if not allowed:
        return settings.ENVIRONMENT != "production"
    return user.email.strip().lower() in allowed
