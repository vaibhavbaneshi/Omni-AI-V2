from app.agent.schemas import AgentRoute, ContextBundle, Source, ToolResult, TraceEvent


class ContextAggregator:

    def aggregate(
        self,
        route: AgentRoute,
        tool_results: list[ToolResult],
        traces: list[TraceEvent],
        max_chars: int = 12000
    ):

        sources: list[Source] = []
        seen = set()
        context_sections = []

        for result in tool_results:
            if result.context:
                context_sections.append(
                    f"--- {result.name.upper()} CONTEXT ---\n{result.context}"
                )

            for source in result.sources:
                key = (
                    source.type,
                    source.url or source.source,
                    source.chunk[:120]
                )

                if key in seen:
                    continue

                seen.add(key)
                sources.append(source)

        sources = sorted(
            sources,
            key=lambda source: source.score or 0,
            reverse=True
        )

        context = "\n\n".join(context_sections)

        if len(context) > max_chars:
            context = context[:max_chars] + "\n\n[Context compressed for synthesis]"

        traces.append(
            TraceEvent(
                phase="aggregation",
                status="complete",
                message="Context aggregated",
                metadata={
                    "sources": len(sources),
                    "tools": [result.name for result in tool_results],
                    "context_chars": len(context)
                }
            )
        )

        return ContextBundle(
            context=context,
            sources=sources,
            tool_results=tool_results,
            route=route,
            traces=traces,
            metadata={
                "source_count": len(sources),
                "context_chars": len(context)
            }
        )
