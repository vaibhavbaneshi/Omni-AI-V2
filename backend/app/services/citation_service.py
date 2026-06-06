"""Normalize retrieval sources into stable document citations."""

from __future__ import annotations

from typing import Any


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_citation(source: dict, index: int) -> dict:
    metadata = dict(source.get("metadata") or {})
    document_name = (
        metadata.get("filename")
        or metadata.get("source")
        or source.get("source")
        or source.get("title")
        or "Document"
    )
    page_number = _coerce_int(metadata.get("page_number") or metadata.get("page"))
    chunk_index = _coerce_int(metadata.get("chunk_index"))
    chunk_id = metadata.get("chunk_id") or (
        f"{metadata.get('document_id')}:{chunk_index}"
        if metadata.get("document_id") and chunk_index is not None
        else f"{document_name}:{chunk_index if chunk_index is not None else index}"
    )
    citation_id = metadata.get("citation_id") or f"S{index + 1}"

    metadata.update(
        {
            "citation_id": citation_id,
            "document_name": str(document_name),
            "chunk_id": str(chunk_id),
            "source_reference": (
                f"{document_name}"
                f"{f' p.{page_number}' if page_number is not None else ''}"
                f" chunk {chunk_index if chunk_index is not None else index}"
            ),
        }
    )
    if page_number is not None:
        metadata["page_number"] = page_number
    if chunk_index is not None:
        metadata["chunk_index"] = chunk_index

    normalized = dict(source)
    normalized["title"] = source.get("title") or str(document_name)
    normalized["source"] = source.get("source") or str(document_name)
    normalized["metadata"] = metadata
    return normalized


def normalize_citations(sources: list[dict]) -> list[dict]:
    return [normalize_citation(source, index) for index, source in enumerate(sources)]


def format_cited_context(sources: list[dict]) -> list[str]:
    cited_chunks: list[str] = []
    for source in normalize_citations(sources):
        metadata = source.get("metadata") or {}
        citation_id = metadata.get("citation_id")
        document_name = metadata.get("document_name") or source.get("source") or "Document"
        page_number = metadata.get("page_number")
        chunk_id = metadata.get("chunk_id")
        page_part = f" | Page: {page_number}" if page_number is not None else ""
        chunk_part = f" | Chunk: {chunk_id}" if chunk_id else ""
        chunk = (source.get("chunk") or "").strip()
        if not chunk:
            continue
        cited_chunks.append(
            f"[{citation_id}] Document: {document_name}{page_part}{chunk_part}\n{chunk}"
        )
    return cited_chunks
