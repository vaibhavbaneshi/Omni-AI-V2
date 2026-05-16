import requests

from app.core.config import settings

# -----------------------------------
# SUMMARIZE CONVERSATION
# -----------------------------------

def summarize_conversation(
    history: str
):

    prompt = f"""
Summarize this conversation.

Keep:
- important facts
- user intent
- technical topics
- decisions made

Conversation:
{history}
"""

    response = requests.post(
        settings.OLLAMA_URL,
        json={
            "model": settings.MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()

    return data["response"]