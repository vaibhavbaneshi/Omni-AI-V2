"""Formal multi-step research agent with persisted report artifacts."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.app_settings import get_settings
from app.core.sanitize import sanitize_retrieved_context
from app.core.telemetry import traced_span
from app.models.research_report import ResearchReport
from app.schemas.agent_schemas import ResearchReportPayload
from app.services.hybrid_search import hybrid_search
from app.services.llm_invoke import invoke_generate
from app.services.query_contextualizer_service import resolve_retrieval_query
from app.services.reranker_service import rerank_documents
from app.tools.web_search import web_search

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


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


def _build_report_prompt(*, query: str, evidence: str, iterations: int) -> str:
    return f"""You are a research analyst. Synthesize the collected evidence into a structured research report.
Return ONLY valid JSON with this shape:
{{
  "title": "short report title",
  "executive_summary": "2-4 sentences",
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "evidence_summary": "paragraph summarizing supporting evidence",
  "sources_reviewed": ["source label 1", "source label 2"],
  "open_questions": ["question 1"],
  "methodology": "brief note on how evidence was gathered",
  "iterations": {iterations}
}}

Rules:
- Base findings ONLY on the evidence below.
- Use empty arrays when unsupported.
- Do not invent citations or facts.

Research question: {query}

EVIDENCE:
{evidence}

JSON:"""


def _format_report_context(payload: ResearchReportPayload) -> str:
    sections = [
        f"# Research Report: {payload.title or 'Analysis'}",
        f"\n## Executive Summary\n{payload.executive_summary}",
    ]
    if payload.key_findings:
        sections.append("\n## Key Findings\n" + "\n".join(f"- {item}" for item in payload.key_findings))
    if payload.evidence_summary:
        sections.append(f"\n## Evidence Summary\n{payload.evidence_summary}")
    if payload.open_questions:
        sections.append("\n## Open Questions\n" + "\n".join(f"- {item}" for item in payload.open_questions))
    return "\n".join(sections)


def _collect_evidence(
    *,
    query: str,
    user_id: int,
    workspace_id: str,
    collection_id: int | None,
    session_id: int | None,
    max_iterations: int,
    history: str = "",
) -> tuple[list[str], list[str], list[str], list[dict], list[dict]]:
    retrieval_query, _ = resolve_retrieval_query(
        query,
        history=history,
        user_id=user_id,
        session_id=session_id,
    )

    refined_query = retrieval_query
    document_chunks: list[str] = []
    web_snippets: list[str] = []
    web_sources: list[dict] = []
    traces: list[dict] = []

    for step in range(1, max_iterations + 1):
        with traced_span("research.iteration", step=step, query=refined_query):
            docs = hybrid_search(
                query=refined_query,
                top_k=8,
                user_id=user_id,
                workspace_id=workspace_id,
                collection_id=collection_id,
                session_id=session_id,
            )
            reranked = rerank_documents(query=refined_query, documents=docs, top_k=4)
            document_chunks = list(dict.fromkeys(document_chunks + reranked))

            web_result = web_search(refined_query)
            snippet = (web_result.context or "").strip()
            if snippet:
                web_snippets.append(snippet)
            for source in web_result.sources:
                web_sources.append(source.to_dict())

            traces.append(
                {
                    "step": step,
                    "query": refined_query,
                    "doc_hits": len(reranked),
                    "web_hit": bool(snippet),
                }
            )

            if step == max_iterations:
                break

            top_terms = " ".join(refined_query.split()[:12])
            refined_query = f"{top_terms} supporting evidence analysis"

    source_labels = [f"document-chunk-{index + 1}" for index in range(min(len(document_chunks), 6))]
    source_labels.extend(f"web-source-{index + 1}" for index in range(min(len(web_snippets), 3)))

    return document_chunks, web_snippets, source_labels, traces, web_sources


def _verify_report(*, query: str, evidence: str, payload: ResearchReportPayload) -> dict[str, Any]:
    prompt = f"""You are a fact-checking agent. Compare the draft research report against the evidence.
Return ONLY valid JSON:
{{"verified": true, "unsupported_claims": ["..."], "confidence": "high|medium|low", "notes": "..."}}

Research question: {query}

DRAFT REPORT:
{payload.model_dump_json()[:6000]}

EVIDENCE:
{evidence[:6000]}

JSON:"""
    try:
        raw = invoke_generate(prompt, temperature=0.1, timeout=60, endpoint="agent.research.verify")
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
    except Exception:
        logger.exception("Research verification step failed")
    return {"verified": True, "unsupported_claims": [], "confidence": "medium", "notes": "Verification skipped."}


class ResearchAgent:
    """Iterative retrieval + web research workflow with persisted report artifact."""

    def run(
        self,
        *,
        query: str,
        user_id: int,
        db: Session,
        workspace_id: str = "default",
        collection_id: int | None = None,
        session_id: int | None = None,
        history: str = "",
        max_iterations: int = 3,
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
            document_chunks, web_snippets, source_labels, traces, web_sources = _collect_evidence(
                query=query,
                user_id=user_id,
                workspace_id=workspace_id,
                collection_id=collection_id,
                session_id=session_id,
                max_iterations=max_iterations,
                history=history,
            )

            raw_evidence = sanitize_retrieved_context(document_chunks + web_snippets[:3])
            prompt = _build_report_prompt(
                query=query,
                evidence=raw_evidence,
                iterations=max_iterations,
            )
            raw_report = invoke_generate(
                prompt,
                temperature=0.25,
                timeout=180,
                endpoint="agent.research.report",
                user_id=user_id,
                session_id=session_id,
            )
            parsed = _extract_json(raw_report)
            parsed["iterations"] = max_iterations
            payload = ResearchReportPayload.model_validate(parsed)

            verification = _verify_report(query=query, evidence=raw_evidence, payload=payload)
            payload.verification = verification
            if verification.get("unsupported_claims"):
                payload.open_questions = list(
                    dict.fromkeys(
                        payload.open_questions
                        + [f"Verify: {claim}" for claim in verification["unsupported_claims"][:5]]
                    )
                )

            record.report = payload.model_dump()
            record.traces = traces
            record.status = "ready"
            record.error_message = None
            db.commit()
            db.refresh(record)

            context = _format_report_context(payload)
            sources = [
                {"type": "document", "label": label, "title": label, "source": label, "chunk": ""}
                for label in source_labels
                if label.startswith("document")
            ]
            sources.extend(
                {
                    "type": "web",
                    "label": source.get("title") or source.get("source") or "Web",
                    "title": source.get("title") or "Web",
                    "source": source.get("source") or "web",
                    "chunk": source.get("chunk") or "",
                    "url": source.get("url"),
                }
                for source in web_sources[:3]
            )

            logger.info(
                "Research report ready report_id=%s user_id=%s findings=%s",
                record.id,
                user_id,
                len(payload.key_findings),
            )

            return self._agent_result(
                context=context,
                sources=sources,
                traces=traces,
                report_id=record.id,
                report=payload,
                retrieval_query=query,
            )
        except Exception as exc:
            record.status = "failed"
            record.error_message = str(exc)[:2000]
            record.traces = traces if "traces" in locals() else []
            db.commit()
            logger.exception("Research agent failed report_id=%s user_id=%s", record.id, user_id)
            raise

    def _agent_result(
        self,
        *,
        context: str,
        sources: list[dict],
        traces: list[dict],
        report_id: int,
        report: ResearchReportPayload,
        retrieval_query: str,
    ) -> dict[str, Any]:
        return {
            "tool": "research-agent",
            "strategy": "research-agent",
            "context": context,
            "sources": sources,
            "route": {
                "strategy": "research-agent",
                "tools": ["retrieval", "web_search"],
                "reason": "Multi-step research agent with persisted report artifact",
                "confidence": 0.92,
                "status": "complete",
            },
            "mode": "research",
            "source_groups": {
                "documents": [source for source in sources if source.get("type") == "document"],
                "web": [source for source in sources if source.get("type") == "web"],
            },
            "tools": ["retrieval", "web_search"],
            "traces": traces,
            "metadata": {
                "agent": "research",
                "report_id": report_id,
                "artifact": report.model_dump(),
                "iterations": report.iterations,
                "retrieval_query": retrieval_query,
            },
            "agent": "research",
            "report_id": report_id,
        }


def get_research_report(
    db: Session,
    *,
    user_id: int,
    report_id: int,
) -> ResearchReport | None:
    return (
        db.query(ResearchReport)
        .filter(
            ResearchReport.id == report_id,
            ResearchReport.user_id == user_id,
        )
        .first()
    )


def report_to_response(record: ResearchReport) -> dict[str, Any]:
    report_payload = None
    if record.report:
        report_payload = ResearchReportPayload.model_validate(record.report).model_dump()

    return {
        "id": record.id,
        "query": record.query,
        "status": record.status,
        "model": record.model,
        "error_message": record.error_message,
        "report": report_payload,
        "traces": record.traces or [],
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def run_research_agent(**kwargs) -> dict[str, Any]:
    from app.services.redis_cache_service import cache_query_result, get_query_cache

    query = kwargs.get("query", "")
    user_id = kwargs.get("user_id")
    cache_key = query.strip().lower()
    if cache_key and user_id is not None:
        cached = get_query_cache("research", cache_key, user_id)
        if cached is not None:
            return cached

    result = ResearchAgent().run(**kwargs)
    if cache_key and user_id is not None and result.get("report_id"):
        cache_query_result("research", cache_key, user_id, result, ttl_seconds=900)
    return result
