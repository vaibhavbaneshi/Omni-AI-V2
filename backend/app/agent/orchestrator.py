from sqlalchemy.orm import Session

from app.core.telemetry import traced_span
from app.agent.context import ContextAggregator
from app.agent.schemas import AgentRoute, ContextBundle, TraceEvent
from app.agent.tools import ToolRegistry
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
    "live"
}

MATH_TERMS = {
    "+",
    "-",
    "*",
    "/",
    "calculate",
    "multiply",
    "divide",
    "sum",
    "percentage"
}

SUMMARY_TERMS = {
    "summarize",
    "summary",
    "brief",
    "tl;dr",
    "recap"
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
        mode: str
    ) -> AgentRoute:

        query_lower = query.lower()
        terms = set(query_lower.replace("?", " ").replace(",", " ").split())
        needs_math = any(term in query_lower for term in MATH_TERMS)
        needs_freshness = bool(terms.intersection(FRESHNESS_TERMS))
        wants_summary = bool(terms.intersection(SUMMARY_TERMS))

        if needs_math:
            return AgentRoute(
                strategy="calculator",
                tools=["calculator", "memory"],
                reason="The request includes a numeric calculation.",
                confidence=0.95,
                mode=mode
            )

        if needs_freshness:
            return AgentRoute(
                strategy="web-rag-hybrid",
                tools=["retrieval", "memory", "web_search"],
                reason="The request may depend on current information.",
                confidence=0.86,
                mode=mode
            )

        if mode == "research":
            return AgentRoute(
                strategy="research-hybrid",
                tools=["retrieval", "memory", "web_search"],
                reason="Research mode checks internal knowledge and external sources.",
                confidence=0.78,
                mode=mode
            )

        if wants_summary:
            return AgentRoute(
                strategy="summarization",
                tools=["retrieval", "memory", "summarizer"],
                reason="The request asks for synthesis over existing context.",
                confidence=0.82,
                mode=mode
            )

        if mode == "coding":
            return AgentRoute(
                strategy="coding-context",
                tools=["retrieval", "memory"],
                reason="Coding mode prioritizes workspace and memory context.",
                confidence=0.75,
                mode=mode
            )

        if mode == "analyst":
            return AgentRoute(
                strategy="analyst-hybrid",
                tools=["retrieval", "memory"],
                reason="Analyst mode prioritizes structured workspace evidence.",
                confidence=0.76,
                mode=mode
            )

        return AgentRoute(
            strategy="workspace-context",
            tools=["retrieval", "memory"],
            reason="The request can likely be answered from workspace context and memory.",
            confidence=0.72,
            mode=mode
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
        history: str = ""
    ) -> ContextBundle:

        traces = [
            TraceEvent(
                phase="routing",
                status="started",
                message="Planning agent route"
            )
        ]

        with traced_span("orchestration.plan", mode=mode):
            route = self.plan(query=query, mode=mode)

        traces.append(
            TraceEvent(
                phase="routing",
                status="complete",
                message=route.reason,
                metadata=route.to_dict()
            )
        )

        results = []

        for tool_name in route.tools:
            traces.append(
                TraceEvent(
                    phase="tool",
                    status="started",
                    message=f"Running {tool_name}",
                    tool=tool_name
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
            traces=traces
        )
