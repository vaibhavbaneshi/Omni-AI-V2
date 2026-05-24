from app.agent.schemas import Source, ToolResult, timed_tool
from app.services.rag_service import retrieve_context_details


def retrieval_tool(
    query: str,
    user_id: int,
    workspace_id: str = "default",
    collection_id: int | None = None,
    **_
):
    finish = timed_tool("retrieval")

    try:
        details = retrieve_context_details(
            query=query,
            user_id=user_id,
            workspace_id=workspace_id,
            collection_id=collection_id
        )

        sources = [
            Source(
                title=source.get("title") or source.get("source") or "Document",
                source=source.get("source") or "Document",
                chunk=source.get("chunk") or "",
                type="document",
                url=source.get("url"),
                score=source.get("score"),
                strategy=source.get("strategy") or "hybrid-semantic-rerank",
                metadata=source.get("metadata") or {}
            )
            for source in details.get("sources", [])
        ]

        return finish(
            ToolResult(
                name="retrieval",
                context=details.get("context", ""),
                sources=sources,
                confidence=max([source.score or 0 for source in sources], default=0),
                metadata={
                    "strategy": details.get("strategy"),
                    "chunks": details.get("chunks", 0)
                }
            )
        )

    except Exception as error:
        return finish(
            ToolResult(
                name="retrieval",
                error=str(error),
                confidence=0
            )
        )
