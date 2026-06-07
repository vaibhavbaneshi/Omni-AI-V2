"""Formal agent workflow APIs — research reports and document analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.document_analysis_agent import run_document_analysis_agent
from app.agent.research_agent import get_research_report, report_to_response, run_research_agent
from app.core.app_settings import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.agent_schemas import (
    DocumentAnalysisResponse,
    DocumentAnalysisRunRequest,
    ResearchReportResponse,
    ResearchRunRequest,
)

router = APIRouter(prefix="/agents", tags=["agents"])


def _require_agent_workflows() -> None:
    settings = get_settings()
    if not settings.ENABLE_AGENT_WORKFLOWS:
        raise HTTPException(status_code=403, detail="Agent workflows are disabled.")


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
