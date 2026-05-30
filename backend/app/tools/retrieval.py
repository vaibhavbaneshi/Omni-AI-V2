from app.agent.schemas import Source, ToolResult, timed_tool
from app.services.attachment_service import is_document_query
from app.services.rag_service import retrieve_context_details, retrieve_session_document_context


def retrieval_tool(
    query: str,
    user_id: int,
    workspace_id: str = "default",
    collection_id: int | None = None,
    session_id: int | None = None,
    db=None,
    **_,
):
    finish = timed_tool("retrieval")

    try:
        # Session-scoped chat uploads: prefer session documents over collection filter.
        effective_collection_id = None if session_id is not None else collection_id

        details = retrieve_context_details(
            query=query,
            user_id=user_id,
            workspace_id=workspace_id,
            collection_id=effective_collection_id,
            session_id=session_id,
        )

        context = details.get("context", "") or ""
        sources_data = details.get("sources", [])

        document_query = is_document_query(query)
        if session_id is not None and db is not None and (
            document_query or len(context.strip()) < 120
        ):
            session_details = retrieve_session_document_context(
                db=db,
                user_id=user_id,
                session_id=session_id,
                workspace_id=workspace_id,
                query=query,
            )
            session_context = session_details.get("context", "") or ""
            if len(session_context.strip()) > len(context.strip()):
                context = session_context
                sources_data = session_details.get("sources", sources_data)
                details["strategy"] = session_details.get("strategy", "session-documents")

        sources = [
            Source(
                title=source.get("title") or source.get("source") or "Document",
                source=source.get("source") or "Document",
                chunk=source.get("chunk") or "",
                type="document",
                url=source.get("url"),
                score=source.get("score"),
                strategy=source.get("strategy") or details.get("strategy") or "hybrid-rerank",
                metadata=source.get("metadata") or {},
            )
            for source in sources_data
        ]

        return finish(
            ToolResult(
                name="retrieval",
                context=context,
                sources=sources,
                confidence=max([source.score or 0 for source in sources], default=0),
                metadata={
                    "strategy": details.get("strategy"),
                    "chunks": details.get("chunks", len(sources)),
                },
            )
        )

    except Exception as error:
        return finish(
            ToolResult(
                name="retrieval",
                error=str(error),
                confidence=0,
            )
        )
