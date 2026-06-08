"""Upload quarantine, scanning, and validation pipeline."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

from app.core.app_settings import get_settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".markdown",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".csv",
    ".json",
    ".html",
    ".htm",
}

BLOCKED_EXTENSIONS = {
    ".exe",
    ".dll",
    ".bat",
    ".cmd",
    ".com",
    ".sh",
    ".bash",
    ".ps1",
    ".js",
    ".mjs",
    ".cjs",
    ".vbs",
    ".jar",
    ".apk",
    ".msi",
    ".scr",
    ".php",
    ".py",
    ".rb",
    ".pl",
}

BLOCKED_MIME_PREFIXES = (
    "application/x-msdownload",
    "application/x-dosexec",
    "application/x-sh",
    "application/javascript",
    "text/javascript",
)

MAX_ZIP_ENTRIES = 200
MAX_ZIP_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_PDF_OBJECTS = 5000


class UploadSecurityError(Exception):
    """Raised when an upload fails security checks."""


def quarantine_directory(user_id: int, session_id: int) -> str:
    settings = get_settings()
    base = settings.UPLOAD_STAGING_DIR.strip() or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "uploads",
        "quarantine",
    )
    path = os.path.join(base, str(user_id), str(session_id))
    os.makedirs(path, exist_ok=True)
    return path


def validate_extension(filename: str) -> None:
    ext = Path(filename).suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        raise UploadSecurityError(f"File type {ext} is not allowed.")
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise UploadSecurityError(f"File type {ext} is not in the allowlist.")


def validate_mime(content_type: str | None) -> None:
    if not content_type:
        return
    lowered = content_type.lower().split(";")[0].strip()
    if any(lowered.startswith(prefix) for prefix in BLOCKED_MIME_PREFIXES):
        raise UploadSecurityError(f"MIME type {lowered} is not allowed.")


def check_zip_bomb(file_path: str) -> None:
    if not file_path.lower().endswith(".zip"):
        return
    try:
        with zipfile.ZipFile(file_path, "r") as archive:
            if len(archive.namelist()) > MAX_ZIP_ENTRIES:
                raise UploadSecurityError("Archive contains too many entries.")
            total = sum(info.file_size for info in archive.infolist())
            if total > MAX_ZIP_UNCOMPRESSED_BYTES:
                raise UploadSecurityError("Archive uncompressed size exceeds limit.")
            for name in archive.namelist():
                if ".." in name or name.startswith("/"):
                    raise UploadSecurityError("Archive contains unsafe paths.")
    except zipfile.BadZipFile as exc:
        raise UploadSecurityError("Invalid ZIP archive.") from exc


def check_pdf_sanity(file_path: str) -> None:
    if not file_path.lower().endswith(".pdf"):
        return
    try:
        with open(file_path, "rb") as handle:
            sample = handle.read(8192)
        if b"/JavaScript" in sample or b"/JS" in sample:
            raise UploadSecurityError("PDF contains embedded JavaScript.")
        if sample.count(b" obj") > MAX_PDF_OBJECTS:
            raise UploadSecurityError("PDF structure exceeds complexity limits.")
    except UploadSecurityError:
        raise
    except OSError as exc:
        raise UploadSecurityError("Unable to read PDF for security checks.") from exc


def scan_with_clamav(file_path: str) -> None:
    settings = get_settings()
    if not settings.CLAMAV_ENABLED:
        return
    socket = settings.CLAMAV_SOCKET.strip() or "/var/run/clamav/clamd.ctl"
    try:
        result = subprocess.run(
            ["clamdscan", "--fdpass", file_path],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if result.returncode == 1 or "FOUND" in output.upper():
            raise UploadSecurityError(f"Malware detected: {output.strip()[:200]}")
        if result.returncode not in (0, 1):
            logger.warning("ClamAV scan inconclusive path=%s output=%s", file_path, output[:200])
    except FileNotFoundError:
        if settings.CLAMAV_REQUIRED:
            raise UploadSecurityError("ClamAV scanner is required but not installed.") from None
        logger.warning("ClamAV not installed — skipping virus scan.")
    except subprocess.TimeoutExpired as exc:
        if settings.CLAMAV_REQUIRED:
            raise UploadSecurityError("ClamAV scan timed out.") from exc
        logger.warning("ClamAV scan timed out — skipping.")


def process_upload_security(
    *,
    quarantine_path: str,
    filename: str,
    content_type: str | None,
    user_id: int,
) -> str:
    """Validate, scan, and approve a quarantined upload. Returns approved path."""
    validate_extension(filename)
    validate_mime(content_type)
    check_zip_bomb(quarantine_path)
    check_pdf_sanity(quarantine_path)
    scan_with_clamav(quarantine_path)
    logger.info(
        "Upload security approved filename=%s user_id=%s path=%s",
        filename,
        user_id,
        quarantine_path,
    )
    return quarantine_path


def move_to_storage(quarantine_path: str, destination_path: str) -> None:
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    shutil.move(quarantine_path, destination_path)
