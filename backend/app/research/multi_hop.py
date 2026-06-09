"""Multi-hop retrieval — iterative evidence gathering across sub-queries."""

from __future__ import annotations

from typing import Any

from app.agent.research_agent import _collect_evidence


def multi_hop_retrieval(
    *,
    plan: dict[str, Any],
    user_id: int,
    workspace_id: str,
    collection_id: int | None,
    session_id: int | None,
    max_iterations: int,
    history: str = "",
) -> tuple[list[str], list[str], list[str], list[dict], list[dict]]:
    queries = plan.get("search_queries") or plan.get("sub_problems") or [plan.get("goal", "")]
    all_chunks: list[str] = []
    all_sources: list[str] = []
    all_labels: list[str] = []
    all_source_dicts: list[dict] = []
    all_traces: list[dict] = []

    per_query_iters = max(1, max_iterations // max(len(queries), 1))
    for sub_query in queries[: max_iterations]:
        chunks, sources, labels, source_dicts, traces = _collect_evidence(
            query=sub_query,
            user_id=user_id,
            workspace_id=workspace_id,
            collection_id=collection_id,
            session_id=session_id,
            max_iterations=per_query_iters,
            history=history,
        )
        all_chunks.extend(chunks)
        all_sources.extend(sources)
        all_labels.extend(labels)
        all_source_dicts.extend(source_dicts)
        all_traces.append({"sub_query": sub_query, "steps": traces})

    return all_chunks, all_sources, all_labels, all_source_dicts, all_traces
