"""Pydantic schemas for formal agent workflows."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResearchReportPayload(BaseModel):
    title: str = ""
    executive_summary: str = ""
    key_findings: list[str] = Field(default_factory=list)
    evidence_summary: str = ""
    sources_reviewed: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    methodology: str = ""
    iterations: int = 0
    verification: dict[str, Any] | None = None


class ResearchRunRequest(BaseModel):
    query: str = Field(min_length=1, max_length=12_000)
    session_id: int | None = None
    workspace_id: str = "default"
    collection_id: int | None = None
    max_iterations: int = Field(default=3, ge=1, le=5)


class ResearchReportResponse(BaseModel):
    id: int
    query: str
    status: str
    model: str | None = None
    error_message: str | None = None
    report: ResearchReportPayload | None = None
    traces: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class DocumentAnalysisRunRequest(BaseModel):
    session_id: int | None = None
    document_id: int | None = None
    workspace_id: str = "default"
    force: bool = False


class DocumentAnalysisArtifact(BaseModel):
    document_id: int
    filename: str
    status: str
    insight_id: int | None = None


class DocumentAnalysisResponse(BaseModel):
    agent: str = "document-analysis"
    status: str
    message: str
    documents: list[DocumentAnalysisArtifact] = Field(default_factory=list)
    context_preview: str = ""


class MultiAgentRunRequest(BaseModel):
    query: str = Field(min_length=1, max_length=12_000)
    session_id: int | None = None
    workspace_id: str = "default"
    collection_id: int | None = None
    mode: str = "research"


class MultiAgentRunResponse(BaseModel):
    trace_id: int
    status: str
    context_preview: str
    agent_steps: list[dict[str, Any]] = Field(default_factory=list)
    planner: dict[str, Any] | None = None
    critic: dict[str, Any] | None = None
    latency_ms: int | None = None


class AgentTraceResponse(BaseModel):
    id: int
    query: str
    status: str
    session_id: int | None = None
    planner_output: dict[str, Any] | None = None
    agent_steps: list[dict[str, Any]] = Field(default_factory=list)
    critic_output: dict[str, Any] | None = None
    final_response_preview: str | None = None
    latency_ms: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
