"""Shared upload staging paths for API + RQ worker."""

from __future__ import annotations

import logging
import os
import tempfile

from app.core.app_settings import get_settings

logger = logging.getLogger(__name__)


def upload_staging_root() -> str:
    """Directory for files awaiting ingestion.

    When RQ is enabled, uploads must live on storage visible to both the API
    and worker (e.g. a Railway volume mounted at /data).
    """
    settings = get_settings()
    if settings.UPLOAD_STAGING_DIR.strip():
        root = settings.UPLOAD_STAGING_DIR.strip()
    elif settings.ingest_uses_rq_queue:
        chroma = settings.CHROMA_DB_PATH.strip()
        if chroma.startswith("/data"):
            root = "/data/uploads"
        else:
            root = os.path.join(os.path.dirname(chroma or "."), "uploads")
    else:
        root = tempfile.gettempdir()

    os.makedirs(root, exist_ok=True)
    return root


def create_upload_directory(*, user_id: int, session_id: int) -> str:
    root = upload_staging_root()
    path = os.path.join(root, f"u{user_id}-s{session_id}-{os.getpid()}")
    os.makedirs(path, exist_ok=True)
    return path
