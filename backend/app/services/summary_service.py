from app.core.llm import get_llm
from app.services.prompt_builder import build_internal_conversation_summary_prompt


def summarize_conversation(history: str) -> str:
    prompt = build_internal_conversation_summary_prompt(history)

    try:
        provider = get_llm()
        return provider.generate(prompt, temperature=0.2, timeout=60)
    except Exception:
        return ""
