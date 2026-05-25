"""Upload validation helpers."""

from __future__ import annotations

import os

from fastapi import HTTPException, UploadFile

PDF_MAGIC = b"%PDF"
ALLOWED_EXTENSIONS = {".pdf"}


async def validate_pdf_upload(file: UploadFile, *, max_bytes: int) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    if file.content_type and file.content_type not in {
        "application/pdf",
        "application/octet-stream",
    }:
        raise HTTPException(status_code=400, detail="Invalid MIME type; expected application/pdf")

    header = await file.read(5)
    await file.seek(0)
    if not header.startswith(PDF_MAGIC):
        raise HTTPException(status_code=400, detail="File content is not a valid PDF")

    body = await file.read()
    await file.seek(0)
    if len(body) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {max_bytes // (1024 * 1024)}MB",
        )
