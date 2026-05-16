import requests

from app.core.config import settings

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

    response = requests.post(
        settings.OLLAMA_URL,
        json={
            "model": settings.MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()

    return data["response"].strip()