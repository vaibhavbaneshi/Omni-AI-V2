from app.services.llm_invoke import invoke_generate
from app.services.prompt_builder import build_internal_conversation_summary_prompt


def summarize_conversation(history: str) -> str:
    prompt = build_internal_conversation_summary_prompt(history)

    try:
        return invoke_generate(
            prompt,
            temperature=0.2,
            timeout=60,
            endpoint="memory.summarize",
        )
    except Exception:
        return ""
