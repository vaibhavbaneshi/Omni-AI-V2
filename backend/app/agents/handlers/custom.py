"""Custom agent from marketplace template configuration."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.memory import add_memory_entry
from app.models.autonomous_agent import AgentExecution, AutonomousAgent
from app.services.llm_invoke import invoke_generate


def run_custom_agent(
    db: Session,
    *,
    agent: AutonomousAgent,
    execution: AgentExecution,
) -> dict[str, Any]:
    config = agent.config or {}
    prompt = config.get("prompt") or config.get("system_prompt") or agent.description
    if not prompt:
        raise ValueError("Custom agent requires config.prompt")

    user_message = config.get("input") or config.get("query") or agent.name
    full_prompt = f"{prompt.strip()}\n\nTask:\n{user_message.strip()}\n\nResponse:"
    response = invoke_generate(full_prompt, temperature=0.3, endpoint="agent.custom")

    add_memory_entry(
        db,
        agent_id=agent.id,
        execution_id=execution.id,
        memory_type="output",
        content=response[:4000],
    )
    return {
        "summary": response[:500],
        "response": response,
        "tokens_used": 0,
    }
