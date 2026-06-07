"""Session-scoped multi-document retrieval and comparison context."""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.core.sanitize import sanitize_retrieved_context
from app.services.attachment_service import count_session_documents, list_session_documents
from app.services.citation_service import format_cited_context, normalize_citations
from app.services.reranker_service import rerank_documents

logger = logging.getLogger(__name__)

_MULTI_DOC_PATTERNS = re.compile(
    r"\b("
    r"compare|comparison|versus|vs\.?|pros and cons|difference between|differences between|"
    r"both documents|each document|all documents|across (the |all )?(files|documents|pdfs|uploads|attachments)|"
    r"which (document|file|pdf)|between (the |these |both )?(documents|files|pdfs)"
    r")\b",
    re.I,
)

_CHUNKS_PER_DOCUMENT = 4
_MAX_TOTAL_CHUNKS = 16


def is_multi_document_query(query: str) -> bool:
    return bool(_MULTI_DOC_PATTERNS.search(query or ""))


def should_use_multi_document_analysis(
    db: Session,
    *,
    user_id: int,
    session_id: int | None,
    query: str,
    workspace_id: str = "default",
) -> bool:
    if session_id is None or not is_multi_document_query(query):
        return False
    return count_session_documents(
        db,
        user_id=user_id,
        session_id=session_id,
        workspace_id=workspace_id,
    ) >= 2


def group_sources_by_document(sources: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for source in sources:
        metadata = source.get("metadata") or {}
        document_id = metadata.get("document_id") or source.get("source") or "unknown"
        key = str(document_id)
        grouped.setdefault(key, []).append(source)
    return grouped


def retrieve_multi_document_context(
    *,
    db: Session,
    user_id: int,
    session_id: int,
    query: str = "",
    workspace_id: str = "default",
    max_chunks_per_document: int = _CHUNKS_PER_DOCUMENT,
) -> dict:
    """Retrieve and group chunks per uploaded document for comparison Q&A."""
    documents = list_session_documents(
        db,
        user_id=user_id,
        session_id=session_id,
        workspace_id=workspace_id,
    )
    if len(documents) < 2:
        return {"context": "", "sources": [], "strategy": "multi-document", "chunks": 0, "document_groups": {}}

    from app.services.documents_services import get_document_collection

    chroma_collection = get_document_collection()
    all_sources: list[dict] = []
    document_groups: dict[str, dict] = {}
    sections: list[str] = []

    for document in documents:
        try:
            matches = chroma_collection.get(
                where={
                    "$and": [
                        {"user_id": str(user_id)},
                        {"document_id": str(document.id)},
                    ]
                },
                include=["documents", "metadatas"],
            )
        except Exception:
            logger.exception("Multi-doc retrieval failed document_id=%s", document.id)
            matches = {"documents": [], "metadatas": []}

        doc_chunks = [str(chunk) for chunk in (matches.get("documents") or []) if chunk and str(chunk).strip()]
        metadatas = matches.get("metadatas") or []

        if query.strip() and len(doc_chunks) > max_chunks_per_document:
            doc_chunks = rerank_documents(
                query=query,
                documents=doc_chunks,
                top_k=max_chunks_per_document,
            )
        else:
            doc_chunks = doc_chunks[:max_chunks_per_document]

        doc_sources: list[dict] = []
        for index, chunk in enumerate(doc_chunks):
            metadata = metadatas[index] if index < len(metadatas) else {}
            source = {
                "title": document.filename,
                "source": document.filename,
                "chunk": chunk,
                "score": 1.0,
                "strategy": "multi-document",
                "type": "document",
                "metadata": {
                    **(metadata or {}),
                    "document_id": str(document.id),
                    "filename": document.filename,
                },
            }
            doc_sources.append(source)
            all_sources.append(source)

        document_groups[str(document.id)] = {
            "document_id": document.id,
            "filename": document.filename,
            "chunk_count": len(doc_sources),
            "sources": doc_sources,
        }

        if doc_sources:
            body = format_cited_context(normalize_citations(doc_sources))
            sections.append(f"=== Document: {document.filename} (id={document.id}) ===\n{body}")

        if len(all_sources) >= _MAX_TOTAL_CHUNKS:
            break

    ranked_sources = normalize_citations(all_sources[:_MAX_TOTAL_CHUNKS])
    context = sanitize_retrieved_context(sections, max_chunks=_MAX_TOTAL_CHUNKS)

    return {
        "context": context,
        "sources": ranked_sources,
        "strategy": "multi-document",
        "chunks": len(ranked_sources),
        "document_groups": document_groups,
    }
