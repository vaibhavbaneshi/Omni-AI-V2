"""Supported document upload types for ingestion."""

from __future__ import annotations

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",
        ".txt",
        ".docx",
        ".csv",
        ".xlsx",
        ".xls",
    }
)

EXTENSION_CONTENT_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    ".csv": {"text/csv", "application/csv", "text/plain", "application/octet-stream"},
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    },
    ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
}

SUPPORTED_UPLOADS_LABEL = "PDF, TXT, DOCX, CSV, XLS, XLSX"
