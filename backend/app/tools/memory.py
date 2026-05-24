from sqlalchemy.orm import Session

from app.agent.schemas import Source, ToolResult, timed_tool
from app.services.user_memory_service import retrieve_memory_context


def memory_tool(
    query: str,
    user_id: int,
    db: Session,
    workspace_id: str = "default",
    **_
):
    finish = timed_tool("memory")

    try:
        result = retrieve_memory_context(
            db=db,
            user_id=user_id,
            query=query,
            workspace_id=workspace_id
        )

        sources = [
            Source(
                title=source["title"],
                source=source["source"],
                chunk=source["chunk"],
                type="memory",
                score=source.get("score"),
                strategy="memory",
                metadata={
                    "category": source.get("title")
                }
            )
            for source in result["sources"]
        ]

        return finish(
            ToolResult(
                name="memory",
                context=result["context"],
                sources=sources,
                confidence=max([source.score or 0 for source in sources], default=0),
                metadata={
                    "memories": len(sources)
                }
            )
        )

    except Exception as error:
        return finish(
            ToolResult(
                name="memory",
                error=str(error),
                confidence=0
            )
        )
