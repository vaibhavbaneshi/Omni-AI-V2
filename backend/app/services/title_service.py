import requests

from app.core.config import settings
from app.core.ollama import (
    raise_ollama_http_error,
    resolve_ollama_generate_url,
    resolve_ollama_model_name,
)

# -----------------------------------
# GENERATE CHAT TITLE
# -----------------------------------

def generate_chat_title(
    first_message: str
):

    prompt = f"""
Generate a SHORT chat title
for this conversation.

Message:
{first_message}

Rules:
- max 5 words
- no quotes
- concise
"""

    ollama_url = settings.OLLAMA_URL or resolve_ollama_generate_url(
        "http://localhost:11434"
    )
    model = resolve_ollama_model_name(settings.MODEL_NAME, ollama_url)

    try:
        response = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", first_message[:48]).strip() or "New Chat"
    except requests.HTTPError as exc:
        raise_ollama_http_error(exc, generate_url=ollama_url, model=model)
    except requests.RequestException:
        return first_message[:48].strip() or "New Chat"