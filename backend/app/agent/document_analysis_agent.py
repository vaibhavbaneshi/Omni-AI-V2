"""Document analysis agent — load, generate insights, persist, and prepare chat context."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.document_insight_schemas import DocumentInsightPayload, payload_from_dict
from app.services.attachment_service import list_session_documents, session_has_documents
from app.services.document_intelligence_service import generate_document_insights

logger = logging.getLogger(__name__)

_ANALYSIS_PATTERNS = [
    re.compile(
        r"\b(generate|create|extract|produce|build)\b.*\b(insights?|faqs?|action items?)\b",
        re.I,
    ),
    re.compile(
        r"\b(analyze|analyse|deep dive|intelligence report|document analysis)\b.*\b(document|file|pdf|upload|attachment)\b",
        re.I,
    ),
    re.compile(
        r"\b(insights?|faqs?|action items?)\b.*\b(from|for|in)\b.*\b(document|file|pdf|upload|attachment)\b",
        re.I,
    ),
    re.compile(r"\brun document (analysis|intelligence)\b", re.I),
]


def is_document_analysis_request(query: str) -> bool:
    text = (query or "").strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _ANALYSIS_PATTERNS)


def _format_insights_context(*, filename: str, payload: DocumentInsightPayload) -> str:
    sections = [f"=== Document Intelligence: {filename} ==="]

    summary = payload.executive_summary
    if summary.overview:
        sections.append(f"Overview: {summary.overview}")
    if summary.key_findings:
        sections.append("Key findings:\n" + "\n".join(f"- {item}" for item in summary.key_findings))
    if summary.recommendations:
        sections.append("Recommendations:\n" + "\n".join(f"- {item}" for item in summary.recommendations))
    if payload.faqs:
        sections.append("FAQs:")
        for faq in payload.faqs[:6]:
            sections.append(f"Q: {faq.question}\nA: {faq.answer}")
    if payload.action_items:
        sections.append("Action items:")
        for item in payload.action_items[:8]:
            deadline = f" (due {item.deadline})" if item.deadline else ""
            owner = f" — {item.owner}" if item.owner else ""
            sections.append(f"- {item.task}{deadline}{owner}")

    metadata = payload.metadata_insights
    if metadata.topics:
        sections.append("Topics: " + ", ".join(metadata.topics[:8]))
    if metadata.keywords:
        sections.append("Keywords: " + ", ".join(metadata.keywords[:10]))

    return "\n\n".join(sections)


class DocumentAnalysisAgent:
    """Automate Phase A document intelligence as an agent workflow."""

    def run(
        self,
        *,
        query: str,
        user_id: int,
        db: Session,
        workspace_id: str = "default",
        session_id: int | None = None,
        document_id: int | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        if session_id is None and document_id is None:
            raise ValueError("session_id or document_id is required for document analysis.")

        if document_id is not None:
            documents = []
            from app.models.document import DocumentRecord

            document = (
                db.query(DocumentRecord)
                .filter(
                    DocumentRecord.id == document_id,
                    DocumentRecord.user_id == user_id,
                )
                .first()
            )
            if document:
                documents = [document]
        else:
            documents = list_session_documents(
                db,
                user_id=user_id,
                session_id=session_id,
                workspace_id=workspace_id,
            )

        if not documents:
            return {
                "tool": "document-analysis-agent",
                "strategy": "document-analysis-agent",
                "context": "",
                "sources": [],
                "route": {
                    "strategy": "document-analysis-agent",
                    "tools": [],
                    "reason": "No uploaded documents available for analysis.",
                    "status": "refused",
                },
                "mode": "analyst",
                "source_groups": {},
                "tools": [],
                "traces": [],
                "metadata": {"agent": "document-analysis", "documents": []},
                "refusal": "No uploaded documents are available to analyze in this session.",
            }

        analyzed: list[dict[str, Any]] = []
        context_sections: list[str] = []
        sources: list[dict] = []

        for document in documents[:3]:
            record = generate_document_insights(
                db,
                user_id=user_id,
                document_id=document.id,
                force=force,
            )
            artifact = {
                "document_id": document.id,
                "filename": document.filename,
                "status": record.status,
                "insight_id": record.id,
            }
            analyzed.append(artifact)

            if record.status == "ready" and record.payload:
                payload = payload_from_dict(record.payload)
                if not payload:
                    continue
                context_sections.append(
                    _format_insights_context(filename=document.filename, payload=payload)
                )
                sources.append(
                    {
                        "title": document.filename,
                        "source": document.filename,
                        "chunk": payload.executive_summary.overview,
                        "type": "document",
                        "strategy": "document-analysis-agent",
                        "metadata": {
                            "document_id": str(document.id),
                            "insight_id": record.id,
                        },
                    }
                )

        context = "\n\n".join(context_sections)
        status = "ready" if any(item["status"] == "ready" for item in analyzed) else "failed"

        logger.info(
            "Document analysis agent complete user_id=%s session_id=%s documents=%s status=%s",
            user_id,
            session_id,
            len(analyzed),
            status,
        )

        return {
            "tool": "document-analysis-agent",
            "strategy": "document-analysis-agent",
            "context": context,
            "sources": sources,
            "route": {
                "strategy": "document-analysis-agent",
                "tools": ["document_intelligence"],
                "reason": "Generated persisted document intelligence artifacts.",
                "confidence": 0.95 if status == "ready" else 0.4,
                "status": status,
            },
            "mode": "analyst",
            "source_groups": {"documents": sources},
            "tools": ["document_intelligence"],
            "traces": [
                {
                    "phase": "document-analysis",
                    "status": status,
                    "message": f"Analyzed {len(analyzed)} document(s)",
                    "metadata": {"documents": analyzed},
                }
            ],
            "metadata": {
                "agent": "document-analysis",
                "documents": analyzed,
                "artifact_status": status,
            },
            "agent": "document-analysis",
            "document_analysis": analyzed,
        }


def run_document_analysis_agent(**kwargs) -> dict[str, Any]:
    return DocumentAnalysisAgent().run(**kwargs)


def should_run_document_analysis_agent(
    db: Session,
    *,
    query: str,
    user_id: int,
    session_id: int | None,
    workspace_id: str = "default",
) -> bool:
    if not is_document_analysis_request(query):
        return False
    if session_id is None:
        return False
    return session_has_documents(
        db,
        user_id=user_id,
        session_id=session_id,
        workspace_id=workspace_id,
    )
