"""Supported document upload types for ingestion."""

from __future__ import annotations

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",
        ".txt",
        ".md",
        ".markdown",
        ".docx",
    }
)

EXTENSION_CONTENT_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".markdown": {"text/markdown", "text/plain", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
}

SUPPORTED_UPLOADS_LABEL = "PDF, DOCX, TXT, Markdown"
