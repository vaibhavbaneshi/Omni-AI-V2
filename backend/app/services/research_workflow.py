"""Multi-step autonomous research workflow (orchestration extension)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.sanitize import sanitize_retrieved_context
from app.core.telemetry import traced_span
from app.services.hybrid_search import hybrid_search
from app.services.reranker_service import rerank_documents
from app.tools.web_search import web_search


def run_deep_research(
    *,
    query: str,
    user_id: int,
    db: Session,
    workspace_id: str = "default",
    collection_id: int | None = None,
    max_iterations: int = 3,
) -> dict:
    """Iteratively refine retrieval and web sources for analyst-style answers."""
    del db  # reserved for future research memory persistence

    refined_query = query
    document_chunks: list[str] = []
    web_snippets: list[str] = []
    traces: list[dict] = []

    for step in range(1, max_iterations + 1):
        with traced_span("research.iteration", step=step, query=refined_query):
            docs = hybrid_search(
                query=refined_query,
                top_k=8,
                user_id=user_id,
                workspace_id=workspace_id,
                collection_id=collection_id,
            )
            reranked = rerank_documents(query=refined_query, documents=docs, top_k=4)
            document_chunks = list(dict.fromkeys(document_chunks + reranked))

            web_result = web_search(refined_query)
            if hasattr(web_result, "context"):
                snippet = web_result.context or ""
            elif isinstance(web_result, dict):
                snippet = web_result.get("answer") or web_result.get("content") or ""
            else:
                snippet = str(web_result)
            if snippet:
                web_snippets.append(snippet.strip())

            traces.append(
                {
                    "step": step,
                    "query": refined_query,
                    "doc_hits": len(reranked),
                    "web_hit": bool(snippet),
                }
            )

            if step == max_iterations:
                break

            # Simple query refinement heuristic for next iteration
            top_terms = " ".join(refined_query.split()[:12])
            refined_query = f"{top_terms} evidence sources analysis"

    context = sanitize_retrieved_context(document_chunks + web_snippets[:3])
    sources = [
        {"type": "document", "label": f"chunk-{index + 1}"}
        for index in range(min(len(document_chunks), 6))
    ]
    sources.extend(
        {"type": "web", "label": f"web-{index + 1}"}
        for index in range(min(len(web_snippets), 3))
    )

    return {
        "tool": "deep-research",
        "strategy": "deep-research",
        "context": context,
        "sources": sources,
        "route": {
            "strategy": "deep-research",
            "tools": ["retrieval", "web_search"],
            "reason": "Multi-step research workflow",
            "confidence": 0.9,
        },
        "mode": "research",
        "source_groups": {"documents": document_chunks[:6], "web": web_snippets[:3]},
        "tools": ["retrieval", "web_search"],
        "traces": traces,
        "metadata": {"iterations": max_iterations},
    }
