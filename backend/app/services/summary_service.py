import requests

from app.core.config import settings
from app.core.ollama import (
    resolve_ollama_generate_url,
    resolve_ollama_model_name,
)
from app.services.prompt_builder import build_internal_conversation_summary_prompt

# -----------------------------------
# SUMMARIZE CONVERSATION
# -----------------------------------

def summarize_conversation(
    history: str
):

    prompt = build_internal_conversation_summary_prompt(history)

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
        return data.get("response", "")
    except requests.RequestException:
        return ""