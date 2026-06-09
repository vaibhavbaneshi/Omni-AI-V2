"""Research report synthesis with confidence and references."""

from __future__ import annotations

import json
import re
from typing import Any

from app.schemas.agent_schemas import ResearchReportPayload
from app.services.llm_invoke import invoke_generate

_JSON_BLOCK = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def generate_report(
    *,
    query: str,
    evidence: str,
    iterations: int,
    verification: dict[str, Any],
    contradictions: dict[str, Any],
) -> ResearchReportPayload:
    prompt = f"""Synthesize a research report from evidence. Return ONLY JSON:
{{
  "title": "short title",
  "executive_summary": "2-4 sentences",
  "key_findings": ["finding 1", "finding 2"],
  "detailed_analysis": "multi-paragraph analysis",
  "evidence_summary": "summary of evidence",
  "sources_reviewed": ["source 1"],
  "references": [{{"label": "source", "url": "optional"}}],
  "open_questions": ["question"],
  "methodology": "how evidence was gathered",
  "confidence_score": 0.0,
  "contradictions_noted": ["note"],
  "iterations": {iterations}
}}

Rules: base findings ONLY on evidence. Include confidence_score 0-1.

Question: {query}

Verification notes: {json.dumps(verification)[:2000]}
Contradictions: {json.dumps(contradictions)[:2000]}

EVIDENCE:
{evidence[:14000]}
JSON:"""
    raw = invoke_generate(prompt, temperature=0.2, endpoint="research.synthesis")
    text = raw.strip()
    block = _JSON_BLOCK.search(text)
    if block:
        text = block.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    payload = json.loads(text[start : end + 1])
    if verification.get("confidence_score") is not None and "confidence_score" not in payload:
        payload["confidence_score"] = verification["confidence_score"]
    payload.setdefault("iterations", iterations)
    return ResearchReportPayload.model_validate(payload)
