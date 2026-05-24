from app.agent.schemas import Source, ToolResult, timed_tool
from app.tools.web_search_tool import web_search_tool


def web_search(
    query: str,
    **_
):
    finish = timed_tool("web_search")

    result = web_search_tool(query)

    sources = [
        Source(
            title=source.get("title") or source.get("source") or "Web result",
            source=source.get("source") or "web",
            chunk=source.get("chunk") or "",
            type="web",
            url=source.get("url"),
            score=source.get("score"),
            strategy=source.get("strategy") or "web-search",
            metadata=source.get("metadata") or {}
        )
        for source in result.get("sources", [])
    ]

    return finish(
        ToolResult(
            name="web_search",
            context=result.get("context", ""),
            sources=sources,
            confidence=0.8 if sources else 0,
            metadata={
                "status": result.get("status"),
                "provider": result.get("provider", "unknown"),
                "results": len(sources)
            },
            error=result.get("error") if result.get("status") == "error" else None
        )
    )
