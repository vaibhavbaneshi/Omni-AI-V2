"""Deep research orchestration pipeline."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.agent.research_agent import _format_report_context, report_to_response
from app.core.app_settings import get_settings
from app.core.sanitize import sanitize_retrieved_context
from app.models.research_report import ResearchReport
from app.research.contradiction import detect_contradictions
from app.research.multi_hop import multi_hop_retrieval
from app.research.planner import plan_research
from app.research.report_generator import generate_report
from app.research.verification import verify_sources

logger = logging.getLogger(__name__)


def run_deep_research(
    db: Session,
    *,
    query: str,
    user_id: int,
    workspace_id: str = "default",
    collection_id: int | None = None,
    session_id: int | None = None,
    max_iterations: int = 3,
    history: str = "",
) -> dict[str, Any]:
    settings = get_settings()
    record = ResearchReport(
        user_id=user_id,
        session_id=session_id,
        query=query.strip(),
        status="processing",
        model=settings.GROQ_MODEL,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        plan = plan_research(query)
        chunks, _sources, labels, source_dicts, traces = multi_hop_retrieval(
            plan=plan,
            user_id=user_id,
            workspace_id=workspace_id,
            collection_id=collection_id,
            session_id=session_id,
            max_iterations=max_iterations,
            history=history,
        )
        evidence = sanitize_retrieved_context(chunks)
        verification = verify_sources(query=query, evidence=evidence, sources=source_dicts)
        contradictions = detect_contradictions(query=query, evidence=evidence)
        payload = generate_report(
            query=query,
            evidence=evidence,
            iterations=max_iterations,
            verification=verification,
            contradictions=contradictions,
        )
        context = _format_report_context(payload)
        record.status = "ready"
        record.report = {
            **payload.model_dump(),
            "plan": plan,
            "verification": verification,
            "contradictions": contradictions,
            "confidence_score": payload.model_dump().get("confidence_score") or verification.get("confidence_score"),
        }
        record.traces = traces
        db.commit()
        db.refresh(record)

        return {
            "report_id": record.id,
            "report": record.report,
            "context": context,
            "sources": source_dicts,
            "traces": traces,
            "verification": verification,
            "contradictions": contradictions,
            "tokens_used": 0,
            "cost_usd": None,
        }
    except Exception as exc:
        record.status = "failed"
        record.error_message = str(exc)[:2000]
        db.commit()
        logger.exception("Deep research failed report_id=%s", record.id)
        raise


def list_research_reports(db: Session, *, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    rows = (
        db.query(ResearchReport)
        .filter(ResearchReport.user_id == user_id)
        .order_by(ResearchReport.created_at.desc())
        .limit(limit)
        .all()
    )
    return [report_to_response(row) for row in rows]
