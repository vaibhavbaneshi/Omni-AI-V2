"""Generate and persist structured document intelligence (summaries, FAQs, action items)."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from typing import Any

from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.models.document import DocumentRecord
from app.models.document_entity import DocumentEntity
from app.models.document_insight import DocumentInsight
from app.models.document_timeline import DocumentTimeline
from app.schemas.document_insight_schemas import (
    DocumentInsightPayload,
    StructuredEntity,
    TimelineEvent,
    payload_from_dict,
)
from app.services.document_loaders import DocumentLoadError, load_document
from app.services.llm_invoke import invoke_generate

logger = logging.getLogger(__name__)

_MAX_DOCUMENT_CHARS = 14_000
_JSON_BLOCK = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _truncate(text: str, limit: int = _MAX_DOCUMENT_CHARS) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit] + "\n\n[Document truncated for analysis.]"


def _extract_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty LLM response")

    block = _JSON_BLOCK.search(text)
    if block:
        text = block.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _build_analysis_prompt(*, filename: str, document_text: str) -> str:
    return f"""You are a document intelligence analyst. Analyze the uploaded document and return ONLY valid JSON (no markdown prose outside the JSON).

Document filename: {filename}

Required JSON shape:
{{
  "executive_summary": {{
    "overview": "2-4 sentence overview",
    "key_findings": ["finding 1", "finding 2"],
    "important_points": ["point 1", "point 2"],
    "risks": ["risk 1"] ,
    "recommendations": ["recommendation 1"]
  }},
  "faqs": [
    {{"question": "...", "answer": "..."}}
  ],
  "action_items": [
    {{"task": "...", "deadline": "YYYY-MM-DD or null", "owner": "name or null"}}
  ],
  "metadata_insights": {{
    "keywords": ["..."],
    "topics": ["..."],
    "entities": ["people, orgs, products"],
    "important_dates": ["..."],
    "statistics": ["notable numbers or metrics"],
    "risks": ["risk or compliance issue"],
    "timeline": [
      {{"date": "YYYY-MM-DD or period", "label": "event title", "description": "what happened", "confidence": "high|medium|low"}}
    ],
    "structured_entities": [
      {{"name": "Entity Name", "entity_type": "person|organization|product|location|other", "mentions": 1, "context": "short context"}}
    ]
  }}
}}

Rules:
- Base answers ONLY on the document text below.
- Generate 3-6 FAQs when the document supports them.
- Extract action items only when tasks/deadlines/owners are present or clearly implied.
- Use empty arrays when a section has no supported content.
- Do not invent facts not present in the document.

DOCUMENT TEXT:
{document_text}

JSON:"""


def _load_document_text_from_index(db: Session, document: DocumentRecord) -> str:
    """Rebuild document text from indexed Chroma chunks when the upload file was cleaned up."""
    from app.services.documents_services import get_document_collection

    if document.chunks_created <= 0 and document.indexing_stage != "ready":
        raise FileNotFoundError("Document has not been indexed yet.")

    chroma_collection = get_document_collection()
    try:
        matches = chroma_collection.get(
            where={
                "$and": [
                    {"user_id": str(document.user_id)},
                    {"document_id": str(document.id)},
                ]
            },
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        raise FileNotFoundError("Document text is not available for analysis.") from exc

    chunks = matches.get("documents") or []
    metadatas = matches.get("metadatas") or []
    if not chunks:
        raise FileNotFoundError("Document text is not available for analysis.")

    ordered: list[tuple[str, dict]] = []
    for index, chunk in enumerate(chunks):
        if not chunk or not str(chunk).strip():
            continue
        metadata = metadatas[index] if index < len(metadatas) else {}
        ordered.append((str(chunk), metadata or {}))

    ordered.sort(key=lambda item: int(item[1].get("chunk_index", 0) or 0))
    combined = "\n\n".join(chunk for chunk, _ in ordered).strip()
    if not combined:
        raise FileNotFoundError("Document text is not available for analysis.")
    return _truncate(combined)


def _load_document_text(db: Session, document: DocumentRecord) -> str:
    if document.storage_path and os.path.exists(document.storage_path):
        try:
            return _truncate(load_document(document.storage_path))
        except DocumentLoadError as exc:
            raise ValueError(str(exc)) from exc

    return _load_document_text_from_index(db, document)


def get_document_insight(
    db: Session,
    *,
    user_id: int,
    document_id: int,
) -> DocumentInsight | None:
    return (
        db.query(DocumentInsight)
        .join(DocumentRecord, DocumentRecord.id == DocumentInsight.document_id)
        .filter(
            DocumentInsight.document_id == document_id,
            DocumentRecord.user_id == user_id,
        )
        .first()
    )


def _get_owned_document(db: Session, *, user_id: int, document_id: int) -> DocumentRecord | None:
    return (
        db.query(DocumentRecord)
        .filter(
            DocumentRecord.id == document_id,
            DocumentRecord.user_id == user_id,
        )
        .first()
    )


def generate_document_insights(
    db: Session,
    *,
    user_id: int,
    document_id: int,
    force: bool = False,
) -> DocumentInsight:
    document = _get_owned_document(db, user_id=user_id, document_id=document_id)
    if not document:
        raise LookupError("Document not found")

    if document.indexing_stage != "ready" and document.chunks_created <= 0:
        raise ValueError("Document must be indexed before generating insights.")

    record = get_document_insight(db, user_id=user_id, document_id=document_id)
    if record is None:
        record = DocumentInsight(
            document_id=document_id,
            user_id=user_id,
            status="processing",
        )
        db.add(record)
    elif record.status == "ready" and not force:
        return record
    else:
        record.status = "processing"
        record.error_message = None

    db.commit()
    db.refresh(record)

    settings = get_settings()
    model_name = settings.GROQ_MODEL

    try:
        document_text = _load_document_text(db, document)
        prompt = _build_analysis_prompt(filename=document.filename, document_text=document_text)
        raw = invoke_generate(
            prompt,
            temperature=0.2,
            timeout=180,
            endpoint="document.intelligence.generate",
            user_id=user_id,
            session_id=document.session_id,
        )
        parsed = _extract_json(raw)
        payload = DocumentInsightPayload.model_validate(parsed)

        record.payload = payload.model_dump()
        record.status = "ready"
        record.model = model_name
        record.error_message = None
        _persist_timeline_and_entities(
            db,
            document_id=document_id,
            user_id=user_id,
            model_name=model_name,
            payload=payload,
        )
        if settings.ENABLE_KNOWLEDGE_GRAPH:
            from app.services.knowledge_graph_service import build_workspace_graph

            try:
                build_workspace_graph(
                    db,
                    user_id=user_id,
                    workspace_id=document.workspace_id or "default",
                    document_id=document_id,
                )
            except Exception:
                logger.exception(
                    "Knowledge graph build failed document_id=%s user_id=%s",
                    document_id,
                    user_id,
                )
        db.commit()
        db.refresh(record)
        logger.info(
            "Document insights generated document_id=%s user_id=%s faqs=%s actions=%s",
            document_id,
            user_id,
            len(payload.faqs),
            len(payload.action_items),
        )
        return record
    except Exception as exc:
        record.status = "failed"
        record.error_message = str(exc)[:2000]
        db.commit()
        db.refresh(record)
        logger.exception(
            "Document insights generation failed document_id=%s user_id=%s",
            document_id,
            user_id,
        )
        return record


def schedule_document_insights_generation(document_id: int) -> None:
    """Fire-and-forget insights generation after indexing (non-blocking)."""
    settings = get_settings()
    if not settings.ENABLE_DOCUMENT_INTELLIGENCE:
        return

    def _run() -> None:
        from app.db.session import SessionLocal

        db = SessionLocal()
        try:
            document = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
            if not document:
                return
            generate_document_insights(
                db,
                user_id=document.user_id,
                document_id=document_id,
                force=False,
            )
        except Exception:
            logger.exception(
                "Background document insights generation failed document_id=%s",
                document_id,
            )
        finally:
            db.close()

    threading.Thread(
        target=_run,
        name=f"doc-insights-{document_id}",
        daemon=True,
    ).start()


def _persist_timeline_and_entities(
    db: Session,
    *,
    document_id: int,
    user_id: int,
    model_name: str,
    payload: DocumentInsightPayload,
) -> None:
    timeline_events = [
        event.model_dump()
        for event in payload.metadata_insights.timeline
        if event.label or event.description or event.date
    ]
    timeline = (
        db.query(DocumentTimeline)
        .filter(DocumentTimeline.document_id == document_id)
        .first()
    )
    if timeline is None:
        timeline = DocumentTimeline(
            document_id=document_id,
            user_id=user_id,
            events=timeline_events,
            model=model_name,
        )
        db.add(timeline)
    else:
        timeline.events = timeline_events
        timeline.model = model_name
        timeline.user_id = user_id

    db.query(DocumentEntity).filter(DocumentEntity.document_id == document_id).delete()

    structured = payload.metadata_insights.structured_entities or []
    if not structured and payload.metadata_insights.entities:
        structured = [
            StructuredEntity(name=name, entity_type="unknown", mentions=1)
            for name in payload.metadata_insights.entities
            if name.strip()
        ]

    for entity in structured:
        if not entity.name.strip():
            continue
        db.add(
            DocumentEntity(
                document_id=document_id,
                user_id=user_id,
                name=entity.name.strip()[:512],
                entity_type=(entity.entity_type or "unknown")[:64],
                mentions=max(entity.mentions or 1, 1),
                context=entity.context,
            )
        )


def _load_timeline_events(db: Session, document_id: int) -> list[dict[str, Any]]:
    record = db.query(DocumentTimeline).filter(DocumentTimeline.document_id == document_id).first()
    if not record or not record.events:
        return []
    return list(record.events)


def _load_structured_entities(db: Session, document_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(DocumentEntity)
        .filter(DocumentEntity.document_id == document_id)
        .order_by(DocumentEntity.mentions.desc(), DocumentEntity.name.asc())
        .all()
    )
    return [
        {
            "name": row.name,
            "entity_type": row.entity_type,
            "mentions": row.mentions,
            "context": row.context,
        }
        for row in rows
    ]


def insight_to_response(record: DocumentInsight, db: Session | None = None) -> dict[str, Any]:
    payload = payload_from_dict(record.payload)
    timeline: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    if db is not None:
        timeline = _load_timeline_events(db, record.document_id)
        entities = _load_structured_entities(db, record.document_id)
    elif payload:
        timeline = [event.model_dump() for event in payload.metadata_insights.timeline]
        entities = [entity.model_dump() for entity in payload.metadata_insights.structured_entities]

    return {
        "document_id": record.document_id,
        "status": record.status,
        "model": record.model,
        "error_message": record.error_message,
        "payload": payload.model_dump() if payload else None,
        "timeline": timeline,
        "entities": entities,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
