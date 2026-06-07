"""Prompt templates for chat generation (keeps internal context out of user-visible output)."""

from __future__ import annotations

import re

_CODING_HINTS = re.compile(
    r"\b(code|boilerplate|component|react|typescript|javascript|python|function|api|snippet|implement|refactor|debug)\b",
    re.I,
)
_COMPARISON_HINTS = re.compile(r"\b(compare|comparison|versus|vs\.?|pros and cons|difference between)\b", re.I)
_PROCESS_HINTS = re.compile(r"\b(how do i|how to|build|create|set up|setup|implement|steps?|workflow|process)\b", re.I)
_DEFINITION_HINTS = re.compile(r"\b(what is|define|explain|overview of|introduction to)\b", re.I)


def looks_like_coding_request(query: str, mode: str) -> bool:
    if mode == "coding":
        return True
    return bool(_CODING_HINTS.search(query or ""))


def _answer_format_instructions(
    query: str,
    effective_mode: str,
    *,
    document_summary: bool = False,
) -> str:
    query = query or ""

    if document_summary:
        return """
ANSWER FORMAT (mandatory for uploaded document analysis):
Use this exact section order with Markdown headings:

# Executive Summary
2-4 sentences with the direct answer.

## Key Findings
- Finding 1
- Finding 2
- Finding 3

## Details
Expanded explanation with short paragraphs and bullets where helpful.

## Risks
- Risk or limitation 1
- Risk or limitation 2
(Use "None identified" only when the document truly supports that.)

## Recommendations
- Action 1
- Action 2
"""

    if _COMPARISON_HINTS.search(query):
        return """
ANSWER FORMAT (mandatory for comparison requests):
# Summary
Brief direct answer in 1-3 sentences.

## Key Points
- Most important difference 1
- Most important difference 2
- Most important difference 3

## Feature Comparison
Use a Markdown table when there are clear dimensions to compare.

## Details
Expanded comparison with concise paragraphs.

## Recommendations
- Best option and when to choose it
- Alternative option and trade-offs
"""

    if effective_mode == "coding":
        return """
ANSWER FORMAT (mandatory for coding/technical requests):
# Summary
Brief direct answer in 1-3 sentences.

## Key Points
- Important constraint or approach
- Setup or dependency note
- Gotcha or best practice

## Details
Use numbered "## Step 1: ...", "## Step 2: ..." sections when implementing.
Put all code in fenced blocks with the correct language tag.
Add a short explanation before or after each code block.

## Recommendations
- Next step or improvement
- Testing or validation step
"""

    if _PROCESS_HINTS.search(query):
        return """
ANSWER FORMAT (mandatory for process/how-to requests):
# Summary
Brief direct answer in 1-3 sentences.

## Key Points
- Prerequisite or requirement
- Core approach
- Expected outcome

## Details
Use numbered sections: "## Step 1: ...", "## Step 2: ...", etc.
Include commands, examples, or scenarios when relevant.

## Recommendations
- Follow-up action
- Common pitfall to avoid
"""

    if _DEFINITION_HINTS.search(query):
        return """
ANSWER FORMAT (mandatory for definition/explanation requests):
# Summary
Brief definition in 1-3 sentences.

## Key Points
- Core concept 1
- Core concept 2
- Core concept 3

## Details
Use sections such as "## How It Works", "## Key Features", and "## Example Use Cases" when helpful.

## Recommendations
- When to use it
- What to explore next
"""

    return """
ANSWER FORMAT (mandatory default):
Use this exact section order with Markdown headings:

# Summary
Short direct answer in 1-3 sentences.

## Key Points
- Point 1
- Point 2
- Point 3

## Details
Expanded explanation with short paragraphs. Use bullets for lists of items.

## Recommendations
- Action 1
- Action 2
(Omit only when recommendations would be artificial.)
"""


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
Answer in polished, professional Markdown.
Write like a knowledgeable expert synthesizing the material, not like a retrieval system repeating chunks.
Use the required section headings, readable paragraphs, and tight bullet lists. Avoid filler and repetition.
Cite document sources inline when reference material is present and source names are available.
""",
        "coding": """
The user wants technical help or code.
Prioritize a working solution, correct code, and practical setup notes.
Prefer modern React (function components, ES modules) when frontend code is requested.
Indent code consistently with 2 spaces unless the language convention differs.
""",
        "writing": """
Improve clarity and structure while preserving intent.
Return polished prose with natural flow; avoid meta-commentary about the task.
Still use the required Markdown section headings for scanability.
""",
        "analyst": """
Present findings clearly using the required section structure.
Use structured bullets when comparing options. Stay concise and readable.
""",
    }

    mode_block = mode_instructions.get(effective_mode, mode_instructions["research"])
    answer_format_block = _answer_format_instructions(
        query,
        effective_mode,
        document_summary=document_summary,
    )

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
- The user uploaded a document to THIS chat. The text above is from that uploaded file.
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
- ALWAYS use Markdown headings (# and ##), bullet lists, and short paragraphs.
- NEVER reply as one large unbroken text block.
- Synthesize retrieved content: analyze it, extract the key facts, merge duplicates, and rewrite naturally.
- Never dump raw retrieved chunks or long copied passages into the final answer.
- When retrieved context contains source labels like [S1], cite factual claims with those labels.
- If document metadata is present, preserve source meaning naturally, for example "According to [S2]..." or bullets ending with "[S2]".
- NEVER output sections or headings such as: "Organized Answer", "Important Facts", "User Intent",
  "Technical Topics", "Decisions Made", "ROUTING PLAN", or "CONVERSATION SUMMARY".
- NEVER list or describe your internal tools, routing, or memory process unless the user asks.
- Do not end with filler like "Please let me know if you have questions" unless the user asked for help choosing options.
- Use proper Markdown: clear headings, fenced code blocks for code, consistent spacing, readable bullet hierarchy.
- Highlight important terms, warnings, or decisions with **bold** when it improves scanability.
- Before answering, silently remove duplicated information, ensure headings match content, and confirm all required sections are present.
{grounding_rules}

STYLE FOR THIS TURN:
{mode_block}

{answer_format_block}

{context_section}

USER QUESTION:
{query.strip()}

ASSISTANT RESPONSE:"""
