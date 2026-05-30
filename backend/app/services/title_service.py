import re

import requests

from app.core.config import settings
from app.core.ollama import (
    raise_ollama_http_error,
    resolve_ollama_generate_url,
    resolve_ollama_model_name,
)


def _clean_title(raw: str, *, fallback: str = "New Chat") -> str:
    title = (raw or "").strip().replace('"', "").replace("'", "")
    title = re.sub(r"\s+", " ", title)
    words = title.split()
    if not words:
        return fallback
    return " ".join(words[:8])[:60]


def _generate_title(prompt: str, *, fallback: str) -> str:
    ollama_url = settings.OLLAMA_URL or resolve_ollama_generate_url("http://localhost:11434")
    model = resolve_ollama_model_name(settings.MODEL_NAME, ollama_url)

    try:
        response = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return _clean_title(data.get("response", ""), fallback=fallback)
    except requests.HTTPError as exc:
        raise_ollama_http_error(exc, generate_url=ollama_url, model=model)
    except requests.RequestException:
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
