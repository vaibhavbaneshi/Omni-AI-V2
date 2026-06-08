"""Pydantic schemas for document intelligence payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecutiveSummarySection(BaseModel):
    overview: str = ""
    key_findings: list[str] = Field(default_factory=list)
    important_points: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class FaqItem(BaseModel):
    question: str
    answer: str


class ActionItem(BaseModel):
    task: str
    deadline: str | None = None
    owner: str | None = None


class TimelineEvent(BaseModel):
    date: str = ""
    label: str = ""
    description: str = ""
    confidence: str | None = None


class StructuredEntity(BaseModel):
    name: str
    entity_type: str = "unknown"
    mentions: int = 1
    context: str | None = None


class DocumentMetadataInsights(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    important_dates: list[str] = Field(default_factory=list)
    statistics: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    structured_entities: list[StructuredEntity] = Field(default_factory=list)


class DocumentInsightPayload(BaseModel):
    executive_summary: ExecutiveSummarySection = Field(default_factory=ExecutiveSummarySection)
    faqs: list[FaqItem] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    metadata_insights: DocumentMetadataInsights = Field(default_factory=DocumentMetadataInsights)


class DocumentInsightResponse(BaseModel):
    document_id: int
    status: str
    model: str | None = None
    error_message: str | None = None
    payload: DocumentInsightPayload | None = None
    timeline: list[TimelineEvent] = Field(default_factory=list)
    entities: list[StructuredEntity] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class DocumentInsightGenerateResponse(BaseModel):
    document_id: int
    status: str
    message: str


def payload_from_dict(data: dict[str, Any] | None) -> DocumentInsightPayload | None:
    if not data:
        return None
    try:
        return DocumentInsightPayload.model_validate(data)
    except Exception:
        return None
