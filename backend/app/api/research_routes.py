"""Deep research API enhancements — Phase O."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.agent.research_agent import get_research_report, report_to_response
from app.core.app_settings import get_settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.research.export import export_report_markdown, export_report_pdf_bytes
from app.research.pipeline import list_research_reports, run_deep_research
from app.schemas.agent_schemas import ResearchRunRequest

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/reports")
def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"reports": list_research_reports(db, user_id=current_user.id)}


@router.post("/run")
def run_research(
    body: ResearchRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.ENABLE_DEEP_RESEARCH and not settings.ENABLE_AGENT_WORKFLOWS:
        raise HTTPException(status_code=403, detail="Deep research is disabled.")
    try:
        result = run_deep_research(
            db,
            query=body.query,
            user_id=current_user.id,
            workspace_id=body.workspace_id,
            collection_id=body.collection_id,
            session_id=body.session_id,
            max_iterations=body.max_iterations,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    record = get_research_report(db, user_id=current_user.id, report_id=result["report_id"])
    return report_to_response(record) if record else result


@router.get("/reports/{report_id}/export/markdown")
def export_markdown(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_research_report(db, user_id=current_user.id, report_id=report_id)
    if not record or not record.report:
        raise HTTPException(status_code=404, detail="Report not found.")
    content = export_report_markdown(record.report, query=record.query)
    return Response(content=content, media_type="text/markdown")


@router.get("/reports/{report_id}/export/pdf")
def export_pdf(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_research_report(db, user_id=current_user.id, report_id=report_id)
    if not record or not record.report:
        raise HTTPException(status_code=404, detail="Report not found.")
    content = export_report_pdf_bytes(record.report, query=record.query)
    return Response(content=content, media_type="application/pdf")
