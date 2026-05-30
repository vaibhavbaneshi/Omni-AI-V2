import re

from app.core.llm import get_llm


def _clean_title(raw: str, *, fallback: str = "New Chat") -> str:
    title = (raw or "").strip().replace('"', "").replace("'", "")
    title = re.sub(r"\s+", " ", title)
    words = title.split()
    if not words:
        return fallback
    return " ".join(words[:8])[:60]


def _generate_title(prompt: str, *, fallback: str) -> str:
    try:
        provider = get_llm()
        response = provider.generate(prompt, temperature=0.2, timeout=30)
        return _clean_title(response, fallback=fallback)
    except Exception:
        return fallback


def generate_chat_title(first_message: str) -> str:
    fallback = _clean_title(first_message[:48], fallback="New Chat")
    prompt = f"""Create a short chat title (3-6 words) for this conversation opener.
Rules: no quotes, no punctuation at the end, title case, concise and specific.

Message:
{first_message.strip()}

Title:"""
    return _generate_title(prompt, fallback=fallback)


def refine_chat_title(first_message: str, assistant_preview: str = "") -> str:
    fallback = generate_chat_title(first_message)
    preview = (assistant_preview or "").strip()[:400]
    prompt = f"""Create a concise chat title (3-6 words) that captures the conversation topic.
Rules: no quotes, no punctuation at the end, title case, specific not generic.

User message:
{first_message.strip()}
"""
    if preview:
        prompt += f"\nAssistant reply preview:\n{preview}\n"
    prompt += "\nTitle:"
    return _generate_title(prompt, fallback=fallback)


def should_refine_session_title(
    session_title: str,
    *,
    assistant_message_count: int,
) -> bool:
    """Only refine once — after the first assistant reply in a session."""
    return assistant_message_count == 1
