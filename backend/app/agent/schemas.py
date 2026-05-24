from dataclasses import dataclass, field
from time import perf_counter
from typing import Any


@dataclass
class Source:
    title: str
    source: str
    chunk: str
    type: str
    url: str | None = None
    score: float | None = None
    strategy: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "title": self.title,
            "source": self.source,
            "chunk": self.chunk,
            "type": self.type,
            "url": self.url,
            "score": self.score,
            "strategy": self.strategy,
            "metadata": self.metadata
        }


@dataclass
class TraceEvent:
    phase: str
    status: str
    message: str
    tool: str | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "phase": self.phase,
            "status": self.status,
            "message": self.message,
            "tool": self.tool,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata
        }


@dataclass
class ToolResult:
    name: str
    context: str = ""
    sources: list[Source] = field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    latency_ms: int = 0
    traces: list[TraceEvent] = field(default_factory=list)

    def to_dict(self):
        return {
            "name": self.name,
            "context": self.context,
            "sources": [source.to_dict() for source in self.sources],
            "confidence": self.confidence,
            "metadata": self.metadata,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "traces": [trace.to_dict() for trace in self.traces]
        }


@dataclass
class AgentRoute:
    strategy: str
    tools: list[str]
    reason: str
    confidence: float
    mode: str
    status: str = "planned"

    def to_dict(self):
        return {
            "strategy": self.strategy,
            "tools": self.tools,
            "reason": self.reason,
            "confidence": self.confidence,
            "mode": self.mode,
            "status": self.status
        }


@dataclass
class ContextBundle:
    context: str
    sources: list[Source]
    tool_results: list[ToolResult]
    route: AgentRoute
    traces: list[TraceEvent]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_meta(self):
        source_dicts = [source.to_dict() for source in self.sources]

        return {
            "tool": self.route.strategy,
            "strategy": self.route.strategy,
            "mode": self.route.mode,
            "route": self.route.to_dict(),
            "sources": source_dicts,
            "source_groups": {
                "documents": [
                    source
                    for source in source_dicts
                    if source.get("type") == "document"
                ],
                "web": [
                    source
                    for source in source_dicts
                    if source.get("type") == "web"
                ],
                "memory": [
                    source
                    for source in source_dicts
                    if source.get("type") == "memory"
                ]
            },
            "tools": [
                result.to_dict()
                for result in self.tool_results
            ],
            "traces": [
                trace.to_dict()
                for trace in self.traces
            ],
            "metadata": self.metadata
        }


def timed_tool(name: str):
    start = perf_counter()

    def finish(
        result: ToolResult
    ):
        result.latency_ms = int((perf_counter() - start) * 1000)
        result.traces.append(
            TraceEvent(
                phase="tool",
                status="complete" if not result.error else "error",
                message=f"{name} finished",
                tool=name,
                latency_ms=result.latency_ms
            )
        )
        return result

    return finish
