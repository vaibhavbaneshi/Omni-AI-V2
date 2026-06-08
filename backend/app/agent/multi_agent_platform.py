"""Multi-agent orchestration: planner → parallel agents → critic → summary."""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentOrchestrator
from app.core.app_settings import get_settings
from app.models.agent_trace import AgentTrace
from app.services.knowledge_graph_service import graph_rag_context
from app.services.llm_invoke import invoke_generate
from app.services.user_memory_service import list_memories

logger = logging.getLogger(__name__)

AGENT_NAMES = (
    "planner",
    "research",
    "document",
    "web_search",
    "memory",
    "critic",
    "summarization",
)


def _planner_plan(query: str) -> dict[str, Any]:
    prompt = f"""You are a planner agent. Break the user query into 3-5 concrete subtasks for specialist agents.
Return JSON only:
{{"goal": "...", "subtasks": [{{"agent": "research|document|web_search|memory", "task": "..."}}]}}

Query: {query}
JSON:"""
    try:
        raw = invoke_generate(prompt, temperature=0.1, timeout=45, endpoint="agent.planner")
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            import json

            return json.loads(raw[start : end + 1])
    except Exception:
        logger.exception("Planner agent failed")
    return {
        "goal": query,
        "subtasks": [
            {"agent": "research", "task": query},
            {"agent": "document", "task": query},
        ],
    }


def _run_specialist_agents(
    db: Session,
    *,
    query: str,
    user_id: int,
    session_id: int | None,
    workspace_id: str,
    collection_id: int | None,
    mode: str,
    plan: dict[str, Any],
    history: str,
) -> list[dict[str, Any]]:
    orchestrator = AgentOrchestrator()
    steps: list[dict[str, Any]] = []

    for subtask in plan.get("subtasks") or []:
        agent_name = subtask.get("agent") or "research"
        task = subtask.get("task") or query
        step: dict[str, Any] = {"agent": agent_name, "task": task, "status": "ok"}

        try:
            if agent_name == "memory":
                memories = list_memories(db, user_id=user_id, workspace_id=workspace_id)[:8]
                step["output"] = "\n".join(f"- {item.content}" for item in memories) or "No memories."
            elif agent_name == "web_search":
                from app.tools.web_search import web_search

                web_result = web_search(task)
                step["output"] = (web_result.context or "").strip()[:4000]
                step["sources"] = [source.to_dict() for source in web_result.sources]
            elif agent_name == "document":
                bundle = orchestrator.run(
                    task,
                    user_id=user_id,
                    db=db,
                    mode=mode,
                    workspace_id=workspace_id,
                    collection_id=collection_id,
                    session_id=session_id,
                    history=history,
                )
                step["output"] = (bundle.context or "")[:4000]
                step["sources"] = [source.to_dict() for source in bundle.sources]
            else:
                bundle = orchestrator.run(
                    task,
                    user_id=user_id,
                    db=db,
                    mode="research",
                    workspace_id=workspace_id,
                    collection_id=collection_id,
                    session_id=session_id,
                    history=history,
                )
                step["output"] = (bundle.context or "")[:4000]
                step["sources"] = [source.to_dict() for source in bundle.sources]
        except Exception as exc:
            step["status"] = "error"
            step["output"] = str(exc)

        steps.append(step)

    return steps


def _critic_review(query: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = "\n\n".join(
        f"[{step['agent']}] {step.get('output', '')[:1200]}" for step in steps if step.get("output")
    )
    prompt = f"""You are a critic agent. Review evidence quality for the user query.
Return JSON only:
{{"approved": true, "gaps": ["..."], "confidence": "high|medium|low", "notes": "..."}}

Query: {query}

EVIDENCE:
{evidence[:8000]}
JSON:"""
    try:
        raw = invoke_generate(prompt, temperature=0.1, timeout=45, endpoint="agent.critic")
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            import json

            return json.loads(raw[start : end + 1])
    except Exception:
        logger.exception("Critic agent failed")
    return {"approved": True, "gaps": [], "confidence": "medium", "notes": "Critic fallback."}


def run_multi_agent_platform(
    db: Session,
    *,
    query: str,
    user_id: int,
    session_id: int | None = None,
    workspace_id: str = "default",
    collection_id: int | None = None,
    mode: str = "research",
    history: str = "",
) -> dict[str, Any]:
    settings = get_settings()
    started = time.perf_counter()
    trace = AgentTrace(user_id=user_id, session_id=session_id, query=query, status="running")
    db.add(trace)
    db.commit()
    db.refresh(trace)

    plan = _planner_plan(query)
    trace.planner_output = plan
    db.commit()

    steps = _run_specialist_agents(
        db,
        query=query,
        user_id=user_id,
        session_id=session_id,
        workspace_id=workspace_id,
        collection_id=collection_id,
        mode=mode,
        plan=plan,
        history=history,
    )
    trace.agent_steps = steps
    db.commit()

    critic = _critic_review(query, steps)
    trace.critic_output = critic
    db.commit()

    graph_context = ""
    if settings.ENABLE_KNOWLEDGE_GRAPH:
        graph_context = graph_rag_context(db, user_id=user_id, query=query, workspace_id=workspace_id)

    evidence = "\n\n".join(
        f"## {step['agent'].title()} Agent\n{step.get('output', '')}" for step in steps if step.get("output")
    )
    if graph_context:
        evidence = f"{graph_context}\n\n{evidence}"

    summary_prompt = f"""You are the summarization agent. Write the final user-facing answer using the evidence.
Use clear Markdown headings, bullet points, and cite sources when present.

User query: {query}

Critic notes: {critic.get('notes', '')}

EVIDENCE:
{evidence[:12000]}

FINAL ANSWER:"""
    final_answer = invoke_generate(
        summary_prompt,
        temperature=0.35,
        timeout=120,
        endpoint="agent.summarization",
        user_id=user_id,
        session_id=session_id,
    )

    from app.services.response_formatter import format_assistant_response

    final_answer = format_assistant_response(final_answer, query=query)

    trace.status = "complete"
    trace.final_response_preview = final_answer[:2000]
    trace.latency_ms = int((time.perf_counter() - started) * 1000)
    db.commit()

    all_sources: list[dict] = []
    for step in steps:
        all_sources.extend(step.get("sources") or [])

    return {
        "agent": "multi-agent-platform",
        "strategy": "multi-agent",
        "context": final_answer,
        "sources": all_sources,
        "tool": "multi-agent",
        "route": {
            "strategy": "multi-agent",
            "tools": list(AGENT_NAMES),
            "reason": plan.get("goal") or query,
            "status": "complete",
        },
        "mode": mode,
        "traces": steps,
        "metadata": {
            "agent": "multi-agent-platform",
            "trace_id": trace.id,
            "planner": plan,
            "critic": critic,
        },
        "trace_id": trace.id,
    }
