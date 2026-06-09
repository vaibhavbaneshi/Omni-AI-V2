"""Source verification and confidence ranking."""

from __future__ import annotations

import json
import re
from typing import Any

from app.services.llm_invoke import invoke_generate

_JSON_BLOCK = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def verify_sources(*, query: str, evidence: str, sources: list[dict]) -> dict[str, Any]:
    prompt = f"""Verify research evidence quality. Return ONLY JSON:
{{
  "confidence_score": 0.0,
  "supported_claims": ["claim 1"],
  "weak_claims": ["claim 2"],
  "source_rankings": [{{"label": "source", "confidence": 0.8, "reason": "why"}}]
}}

Question: {query}
Sources count: {len(sources)}

EVIDENCE:
{evidence[:12000]}
JSON:"""
    raw = invoke_generate(prompt, temperature=0.1, endpoint="research.verification")
    text = raw.strip()
    block = _JSON_BLOCK.search(text)
    if block:
        text = block.group(1).strip()
    try:
        start = text.find("{")
        end = text.rfind("}")
        payload = json.loads(text[start : end + 1]) if start >= 0 else json.loads(text)
    except (json.JSONDecodeError, ValueError):
        payload = {"confidence_score": 0.5, "supported_claims": [], "weak_claims": [], "source_rankings": []}
    payload.setdefault("confidence_score", 0.5)
    return payload
