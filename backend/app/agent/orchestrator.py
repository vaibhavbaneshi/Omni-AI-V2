from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.telemetry import traced_span
from app.agent.context import ContextAggregator
from app.agent.schemas import AgentRoute, ContextBundle, TraceEvent
from app.agent.tools import ToolRegistry
from app.services.attachment_service import (
    is_document_query,
    needs_calculator,
    session_has_documents,
)
from app.tools.calculator import calculator_tool
from app.tools.memory import memory_tool
from app.tools.retrieval import retrieval_tool
from app.tools.summarizer import summarizer_tool
from app.tools.web_search import web_search


FRESHNESS_TERMS = {
    "latest",
    "today",
    "current",
    "recent",
    "news",
    "2025",
    "2026",
    "now",
    "live",
}

SUMMARY_TERMS = {
    "summarize",
    "summary",
    "brief",
    "tl;dr",
    "recap",
}


class AgentOrchestrator:

    def __init__(self):
        self.registry = ToolRegistry()
        self.registry.register("retrieval", retrieval_tool)
        self.registry.register("memory", memory_tool)
        self.registry.register("web_search", web_search)
        self.registry.register("calculator", calculator_tool)
        self.registry.register("summarizer", summarizer_tool)
        self.aggregator = ContextAggregator()

    def plan(
        self,
        query: str,
        mode: str,
        *,
        db: Session | None = None,
        user_id: int | None = None,
        session_id: int | None = None,
        workspace_id: str = "default",
    ) -> AgentRoute:
        query_lower = query.lower()
        terms = set(query_lower.replace("?", " ").replace(",", " ").split())
        document_query = is_document_query(query)
        has_session_docs = (
            session_has_documents(
                db,
                user_id=user_id,
                session_id=session_id,
                workspace_id=workspace_id,
            )
            if db is not None and user_id is not None
            else False
        )

        if document_query:
            return AgentRoute(
                strategy="document-retrieval",
                tools=["retrieval", "memory"],
                reason="The request references an uploaded document; retrieval is required.",
                confidence=0.97,
                mode=mode,
            )

        if needs_calculator(query):
            return AgentRoute(
                strategy="calculator",
                tools=["calculator", "memory"],
                reason="The request includes a numeric calculation.",
                confidence=0.95,
                mode=mode,
            )

        if has_session_docs and any(
            token in query_lower
            for token in ("document", "file", "pdf", "upload", "attachment", "attached")
        ):
            return AgentRoute(
                strategy="session-document-context",
                tools=["retrieval", "memory"],
                reason="This chat has uploaded documents that may be relevant.",
                confidence=0.9,
                mode=mode,
            )

        needs_freshness = bool(terms.intersection(FRESHNESS_TERMS))
        wants_summary = bool(terms.intersection(SUMMARY_TERMS))

        if needs_freshness:
            return AgentRoute(
                strategy="web-rag-hybrid",
                tools=["retrieval", "memory", "web_search"],
                reason="The request may depend on current information.",
                confidence=0.86,
                mode=mode,
            )

        if mode == "research":
            return AgentRoute(
                strategy="research-hybrid",
                tools=["retrieval", "memory", "web_search"],
                reason="Research mode checks internal knowledge and external sources.",
                confidence=0.78,
                mode=mode,
            )

        if wants_summary:
            return AgentRoute(
                strategy="summarization",
                tools=["retrieval", "memory", "summarizer"],
                reason="The request asks for synthesis over existing context.",
                confidence=0.82,
                mode=mode,
            )

        if mode == "coding":
            return AgentRoute(
                strategy="coding-context",
                tools=["retrieval", "memory"],
                reason="Coding mode prioritizes workspace and memory context.",
                confidence=0.75,
                mode=mode,
            )

        if mode == "analyst":
            return AgentRoute(
                strategy="analyst-hybrid",
                tools=["retrieval", "memory"],
                reason="Analyst mode prioritizes structured workspace evidence.",
                confidence=0.76,
                mode=mode,
            )

        return AgentRoute(
            strategy="workspace-context",
            tools=["retrieval", "memory"],
            reason="The request can likely be answered from workspace context and memory.",
            confidence=0.72,
            mode=mode,
        )

    def run(
        self,
        query: str,
        user_id: int,
        db: Session,
        mode: str = "research",
        workspace_id: str = "default",
        collection_id: int | None = None,
        session_id: int | None = None,
        history: str = "",
    ) -> ContextBundle:
        traces = [
            TraceEvent(
                phase="routing",
                status="started",
                message="Planning agent route",
            )
        ]

        with traced_span("orchestration.plan", mode=mode):
            route = self.plan(
                query=query,
                mode=mode,
                db=db,
                user_id=user_id,
                session_id=session_id,
                workspace_id=workspace_id,
            )

        traces.append(
            TraceEvent(
                phase="routing",
                status="complete",
                message=route.reason,
                metadata=route.to_dict(),
            )
        )

        results = []

        for tool_name in route.tools:
            traces.append(
                TraceEvent(
                    phase="tool",
                    status="started",
                    message=f"Running {tool_name}",
                    tool=tool_name,
                )
            )

            with traced_span("orchestration.tool", tool=tool_name, user_id=user_id):
                result = self.registry.execute(
                    tool_name,
                    query=query,
                    user_id=user_id,
                    db=db,
                    mode=mode,
                    workspace_id=workspace_id,
                    collection_id=collection_id,
                    session_id=session_id,
                    history=history,
                )

            results.append(result)
            traces.extend(result.traces)

        route.status = "complete" if not all(result.error for result in results) else "fallback"

        return self.aggregator.aggregate(
            route=route,
            tool_results=results,
            traces=traces,
        )
