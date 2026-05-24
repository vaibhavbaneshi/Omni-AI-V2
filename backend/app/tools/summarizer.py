from app.agent.schemas import ToolResult, timed_tool


def summarizer_tool(
    history: str = "",
    **_
):
    finish = timed_tool("summarizer")

    condensed = history[-2500:] if history else ""

    return finish(
        ToolResult(
            name="summarizer",
            context=f"Conversation summary context:\n{condensed}" if condensed else "",
            confidence=0.7 if condensed else 0,
            metadata={
                "history_chars": len(history or "")
            }
        )
    )
