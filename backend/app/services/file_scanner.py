"""Pluggable upload scanning — delegates to upload security pipeline."""

from __future__ import annotations

import logging

from app.services.upload_security_service import (
    UploadSecurityError,
    process_upload_security,
)

logger = logging.getLogger(__name__)


class FileScanError(Exception):
    """Raised when an uploaded file fails malware scanning."""


def scan_uploaded_file(file_path: str, *, filename: str, user_id: int | None = None) -> None:
    try:
        process_upload_security(
            quarantine_path=file_path,
            filename=filename,
            content_type=None,
            user_id=user_id or 0,
        )
    except UploadSecurityError as exc:
        raise FileScanError(str(exc)) from exc
