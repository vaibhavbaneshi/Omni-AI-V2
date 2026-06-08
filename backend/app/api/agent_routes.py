"""Formal agent workflow APIs — research reports and document analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agent.document_analysis_agent import run_document_analysis_agent
from app.agent.multi_agent_platform import run_multi_agent_platform
from app.agent.research_agent import get_research_report, report_to_response, run_research_agent
from app.core.app_settings import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.agent_trace import AgentTrace
from app.models.user import User
from app.schemas.agent_schemas import (
    AgentTraceResponse,
    DocumentAnalysisResponse,
    DocumentAnalysisRunRequest,
    MultiAgentRunRequest,
    MultiAgentRunResponse,
    ResearchReportResponse,
    ResearchRunRequest,
)

router = APIRouter(prefix="/agents", tags=["agents"])


def _require_agent_workflows() -> None:
    settings = get_settings()
    if not settings.ENABLE_AGENT_WORKFLOWS:
        raise HTTPException(status_code=403, detail="Agent workflows are disabled.")


def _trace_to_response(record: AgentTrace) -> AgentTraceResponse:
    return AgentTraceResponse(
        id=record.id,
        query=record.query,
        status=record.status,
        session_id=record.session_id,
        planner_output=record.planner_output,
        agent_steps=record.agent_steps or [],
        critic_output=record.critic_output,
        final_response_preview=record.final_response_preview,
        latency_ms=record.latency_ms,
        created_at=record.created_at.isoformat() if record.created_at else None,
        updated_at=record.updated_at.isoformat() if record.updated_at else None,
    )


@router.post("/research", response_model=ResearchReportResponse)
def create_research_report(
    body: ResearchRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_agent_workflows()
    settings = get_settings()
    if not settings.ENABLE_DEEP_RESEARCH:
        raise HTTPException(status_code=403, detail="Deep research agent is disabled.")

    try:
        result = run_research_agent(
            query=body.query,
            user_id=current_user.id,
            db=db,
            workspace_id=body.workspace_id,
            collection_id=body.collection_id,
            session_id=body.session_id,
            max_iterations=body.max_iterations,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    report_id = result.get("report_id")
    if not report_id:
        raise HTTPException(status_code=500, detail="Research report was not persisted.")

    record = get_research_report(db, user_id=current_user.id, report_id=report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Research report not found.")
    return report_to_response(record)


@router.get("/research/{report_id}", response_model=ResearchReportResponse)
def read_research_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_research_report(db, user_id=current_user.id, report_id=report_id)
    if not record:
        raise HTTPException(status_code=404, detail="Research report not found.")
    return report_to_response(record)


@router.post("/multi-agent", response_model=MultiAgentRunResponse)
def run_multi_agent(
    body: MultiAgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_agent_workflows()
    settings = get_settings()
    if not settings.ENABLE_MULTI_AGENT:
        raise HTTPException(status_code=403, detail="Multi-agent platform is disabled.")

    try:
        result = run_multi_agent_platform(
            db,
            query=body.query,
            user_id=current_user.id,
            session_id=body.session_id,
            workspace_id=body.workspace_id,
            collection_id=body.collection_id,
            mode=body.mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    trace_id = result.get("trace_id")
    trace = (
        db.query(AgentTrace)
        .filter(AgentTrace.id == trace_id, AgentTrace.user_id == current_user.id)
        .first()
    )
    return MultiAgentRunResponse(
        trace_id=trace_id or 0,
        status=trace.status if trace else "complete",
        context_preview=(result.get("context") or "")[:1200],
        agent_steps=result.get("traces") or [],
        planner=(result.get("metadata") or {}).get("planner"),
        critic=(result.get("metadata") or {}).get("critic"),
        latency_ms=trace.latency_ms if trace else None,
    )


@router.get("/traces", response_model=list[AgentTraceResponse])
def list_agent_traces(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_agent_workflows()
    rows = (
        db.query(AgentTrace)
        .filter(AgentTrace.user_id == current_user.id)
        .order_by(AgentTrace.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_trace_to_response(row) for row in rows]


@router.get("/traces/{trace_id}", response_model=AgentTraceResponse)
def read_agent_trace(
    trace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = (
        db.query(AgentTrace)
        .filter(AgentTrace.id == trace_id, AgentTrace.user_id == current_user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Agent trace not found.")
    return _trace_to_response(record)


@router.post("/document-analysis", response_model=DocumentAnalysisResponse)
def run_document_analysis(
    body: DocumentAnalysisRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_agent_workflows()

    result = run_document_analysis_agent(
        query="Generate document insights",
        user_id=current_user.id,
        db=db,
        workspace_id=body.workspace_id,
        session_id=body.session_id,
        document_id=body.document_id,
        force=body.force,
    )

    if result.get("refusal"):
        raise HTTPException(status_code=400, detail=result["refusal"])

    documents = result.get("document_analysis") or result.get("metadata", {}).get("documents") or []
    status = result.get("route", {}).get("status") or "failed"
    message = (
        "Document analysis completed."
        if status == "ready"
        else "Document analysis did not produce ready insights."
    )

    return DocumentAnalysisResponse(
        status=status,
        message=message,
        documents=documents,
        context_preview=(result.get("context") or "")[:1200],
    )
