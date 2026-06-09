"""LLM research planner — decomposes questions into sub-problems."""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.llm_invoke import invoke_generate

_JSON_BLOCK = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _parse_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    block = _JSON_BLOCK.search(text)
    if block:
        text = block.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start : end + 1])
    return json.loads(text)


def plan_research(query: str) -> dict[str, Any]:
    prompt = f"""You are a research planner. Break the question into sub-problems for retrieval.
Return ONLY JSON:
{{
  "goal": "one sentence research goal",
  "sub_problems": ["sub-question 1", "sub-question 2", "sub-question 3"],
  "search_queries": ["query 1", "query 2", "query 3"]
}}

Question: {query.strip()}
JSON:"""
    raw = invoke_generate(prompt, temperature=0.2, endpoint="research.planner")
    try:
        payload = _parse_json(raw)
    except (json.JSONDecodeError, ValueError):
        payload = {
            "goal": query.strip(),
            "sub_problems": [query.strip()],
            "search_queries": [query.strip()],
        }
    payload.setdefault("goal", query.strip())
    payload.setdefault("sub_problems", [query.strip()])
    payload.setdefault("search_queries", payload.get("sub_problems") or [query.strip()])
    return payload
