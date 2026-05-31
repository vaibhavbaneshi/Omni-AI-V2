"""Pluggable upload scanning layer.

This no-op implementation is the integration point for ClamAV or a managed
malware scanning service. It intentionally fails closed only when a configured
scanner reports a threat; without a scanner, validation still enforces type,
size, and filename restrictions.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class FileScanError(Exception):
    """Raised when an uploaded file fails malware scanning."""


def scan_uploaded_file(file_path: str, *, filename: str, user_id: int | None = None) -> None:
    # TODO: integrate ClamAV here, for example via clamd:
    # result = clamd_client.instream(open(file_path, "rb"))
    # if result indicates malware: raise FileScanError(...)
    logger.info(
        "Upload virus scan hook passed filename=%s path=%s user_id=%s scanner=noop",
        filename,
        file_path,
        user_id,
    )
