"""Prompt templates for chat generation (keeps internal context out of user-visible output)."""

from __future__ import annotations

import re

_CODING_HINTS = re.compile(
    r"\b(code|boilerplate|component|react|typescript|javascript|python|function|api|snippet|implement|refactor|debug)\b",
    re.I,
)


def looks_like_coding_request(query: str, mode: str) -> bool:
    if mode == "coding":
        return True
    return bool(_CODING_HINTS.search(query or ""))


def build_internal_conversation_summary_prompt(history: str) -> str:
    return f"""Write a short internal memory note (2-4 sentences, plain prose only).
Do NOT use headings, bullet lists, or labels such as "User Intent", "Important Facts", or "Decisions Made".
This text is for the assistant only and must never be shown to the user.

Conversation:
{history}
"""


def build_stream_prompt(
    *,
    query: str,
    context: str = "",
    history: str = "",
    summary: str = "",
    mode: str = "research",
    require_grounding: bool = False,
    document_summary: bool = False,
) -> str:
    effective_mode = "coding" if looks_like_coding_request(query, mode) else mode

    mode_instructions = {
        "research": """
Answer directly in clean, natural Markdown.
Lead with the answer, then add supporting detail only when it helps.
Use short paragraphs and tight bullet lists. Avoid filler and repetition.
Cite document sources inline when reference material is present.
""",
        "coding": """
The user wants code. Respond in this order:
1. One short sentence stating what you are providing (optional).
2. A single fenced code block with the full solution (correct language tag, e.g. ```tsx or ```jsx).
3. At most 3 brief bullets for setup or usage notes — only if necessary.

Do not add tutorial links or long explanations unless explicitly asked.
Prefer modern React (function components, ES modules). Indent code consistently (2 spaces).
""",
        "writing": """
Improve clarity and structure while preserving intent.
Return polished prose with natural flow; avoid meta-commentary about the task.
""",
        "analyst": """
Present findings clearly: brief summary, key evidence, implications.
Use structured bullets when comparing options. Stay concise and readable.
""",
    }

    mode_block = mode_instructions.get(effective_mode, mode_instructions["research"])

    blocks: list[str] = []

    if history.strip():
        blocks.append(
            f"""[INTERNAL — prior messages, do not quote these labels in your answer]
{history.strip()}"""
        )

    if summary.strip():
        blocks.append(
            f"""[INTERNAL — conversation memory, do not repeat this structure in your answer]
{summary.strip()}"""
        )

    if context.strip():
        label = (
            "Uploaded document content for this chat — summarize and answer from this text only"
            if document_summary
            else "Reference material — use when relevant; do not invent facts beyond this"
        )
        blocks.append(
            f"""[{label}]
{context.strip()}"""
        )

    context_section = "\n\n".join(blocks) if blocks else "(No additional reference material.)"

    grounding_rules = ""
    if document_summary and context.strip():
        grounding_rules = """
DOCUMENT SUMMARY (mandatory):
- The user uploaded a PDF to THIS chat. The text above is from that uploaded file.
- Summarize or answer using ONLY the uploaded document content above.
- Do NOT say no file was attached — the document text is already provided above.
- Do NOT invent content that is not in the document text.
"""
    elif require_grounding:
        grounding_rules = """
DOCUMENT GROUNDING (mandatory):
- Answer ONLY from the reference material above.
- If reference material is empty or insufficient, say you cannot find the requested document content.
- NEVER invent filenames, sections, or document contents.
"""

    return f"""You are Omni AI, a precise and conversational assistant in a professional workspace.

OUTPUT RULES (mandatory):
- Reply ONLY with content the user should read. No hidden reasoning.
- Write like a thoughtful expert: clear, natural, and easy to scan.
- NEVER output sections or headings such as: "Organized Answer", "Important Facts", "User Intent",
  "Technical Topics", "Decisions Made", "ROUTING PLAN", or "CONVERSATION SUMMARY".
- NEVER list or describe your internal tools, routing, or memory process unless the user asks.
- Do not end with filler like "Please let me know if you have questions" unless the user asked for help choosing options.
- Use proper Markdown: headings sparingly, fenced code blocks for code, consistent spacing, readable bullet hierarchy.
{grounding_rules}

STYLE FOR THIS TURN:
{mode_block}

{context_section}

USER QUESTION:
{query.strip()}

ASSISTANT RESPONSE:"""
