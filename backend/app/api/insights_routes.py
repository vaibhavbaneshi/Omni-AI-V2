"""Document intelligence API — executive summaries, FAQs, action items, metadata."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.document_insight_schemas import (
    DocumentInsightGenerateResponse,
    DocumentInsightResponse,
)
from app.services.document_intelligence_service import (
    generate_document_insights,
    get_document_insight,
    insight_to_response,
)

router = APIRouter(tags=["document-intelligence"])


@router.get("/documents/{document_id}/insights", response_model=DocumentInsightResponse)
def read_document_insights(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = get_document_insight(
        db,
        user_id=current_user.id,
        document_id=document_id,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Insights not found for this document.")
    return insight_to_response(record)


@router.post("/documents/{document_id}/insights/generate", response_model=DocumentInsightGenerateResponse)
def create_document_insights(
    document_id: int,
    force: bool = Query(default=False, description="Regenerate even if insights already exist"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        record = generate_document_insights(
            db,
            user_id=current_user.id,
            document_id=document_id,
            force=force,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Document not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    message = "Insights generated successfully." if record.status == "ready" else "Insight generation failed."
    if record.status == "processing":
        message = "Insight generation in progress."

    return DocumentInsightGenerateResponse(
        document_id=document_id,
        status=record.status,
        message=message,
    )
