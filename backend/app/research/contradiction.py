"""Contradiction detection across evidence sources."""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.llm_invoke import invoke_generate

_JSON_BLOCK = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def detect_contradictions(*, query: str, evidence: str) -> dict[str, Any]:
    prompt = f"""Identify conflicting claims in the evidence. Return ONLY JSON:
{{
  "contradictions": [
    {{"claim_a": "...", "claim_b": "...", "severity": "high|medium|low", "resolution": "how to reconcile"}}
  ],
  "consistent_themes": ["theme 1"]
}}

Question: {query}

EVIDENCE:
{evidence[:12000]}
JSON:"""
    raw = invoke_generate(prompt, temperature=0.1, endpoint="research.contradiction")
    text = raw.strip()
    block = _JSON_BLOCK.search(text)
    if block:
        text = block.group(1).strip()
    try:
        start = text.find("{")
        end = text.rfind("}")
        return json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return {"contradictions": [], "consistent_themes": []}
