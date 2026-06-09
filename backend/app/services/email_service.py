"""Email notification abstraction — logs in dev, SMTP when configured."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.app_settings import get_settings

logger = logging.getLogger(__name__)


def send_email_notification(
    *,
    to_email: str,
    subject: str,
    body: str,
    link: str | None = None,
) -> None:
    settings = get_settings()
    content = body
    if link:
        frontend = settings.FRONTEND_URL.rstrip("/")
        content = f"{body}\n\nOpen: {frontend}{link}"

    if not settings.SMTP_HOST:
        logger.info("Email (dev log) to=%s subject=%s", to_email, subject)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL or "noreply@omniai.local"
    message["To"] = to_email
    message.set_content(content)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)
