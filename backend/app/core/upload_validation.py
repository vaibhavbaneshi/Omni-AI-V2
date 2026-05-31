"""Upload validation helpers."""

from __future__ import annotations

import os
import re
import unicodedata

from fastapi import HTTPException, UploadFile

from app.core.supported_uploads import (
    ALLOWED_EXTENSIONS,
    EXTENSION_CONTENT_TYPES,
    SUPPORTED_UPLOADS_LABEL,
)

PDF_MAGIC = b"%PDF"
ZIP_MAGIC = b"PK\x03\x04"
XLS_MAGIC = b"\xD0\xCF\x11\xE0"
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")
BLOCKED_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".com",
    ".dll",
    ".exe",
    ".js",
    ".php",
    ".ps1",
    ".sh",
    ".zip",
}


def sanitize_upload_filename(filename: str) -> str:
    base = os.path.basename(filename or "").strip().strip(".")
    normalized = unicodedata.normalize("NFKC", base)
    cleaned = SAFE_FILENAME_RE.sub("_", normalized).strip(" .")
    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    if cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    if len(cleaned.encode("utf-8")) > 180:
        name, ext = os.path.splitext(cleaned)
        cleaned = f"{name[:120]}{ext}"
    return cleaned


async def validate_document_upload(file: UploadFile, *, max_bytes: int) -> int:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    safe_name = sanitize_upload_filename(file.filename)
    extension = os.path.splitext(safe_name)[1].lower()
    if extension in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="This file type is not allowed.")

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported formats: {SUPPORTED_UPLOADS_LABEL}.",
        )

    allowed_mimes = EXTENSION_CONTENT_TYPES.get(extension, set())
    if file.content_type and file.content_type not in allowed_mimes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid MIME type for {extension} upload.",
        )

    header = await file.read(8)
    await file.seek(0)

    if extension == ".pdf" and not header.startswith(PDF_MAGIC):
        raise HTTPException(status_code=400, detail="File content is not a valid PDF.")
    if extension in {".docx", ".xlsx"} and not header.startswith(ZIP_MAGIC):
        raise HTTPException(status_code=400, detail=f"File content is not a valid {extension[1:].upper()}.")
    if extension == ".zip":
        raise HTTPException(status_code=400, detail="ZIP uploads are not supported.")
    if extension == ".xls" and not header.startswith(XLS_MAGIC):
        raise HTTPException(status_code=400, detail="File content is not a valid XLS workbook.")

    body = await file.read()
    await file.seek(0)
    if len(body) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {max_bytes // (1024 * 1024)}MB",
        )
    if not body.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    return len(body)


# Backward-compatible alias
validate_pdf_upload = validate_document_upload
