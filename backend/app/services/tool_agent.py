from app.tools.tool_executor import (
    execute_tool
)

def tool_calling_agent(
    query: str
):

    query_lower = query.lower()

    # -----------------------------------
    # CALCULATOR TOOL
    # -----------------------------------

    math_keywords = [
        "+",
        "-",
        "*",
        "/",
        "calculate",
        "multiply",
        "addition"
    ]

    if any(
        word in query_lower
        for word in math_keywords
    ):

        tool = "calculator"

    # -----------------------------------
    # WEB SEARCH TOOL
    # -----------------------------------

    elif any(
        word in query_lower
        for word in [
            "latest",
            "news",
            "today",
            "current"
        ]
    ):

        tool = "web_search"

    # -----------------------------------
    # DEFAULT → RAG
    # -----------------------------------

    else:

        tool = "rag"

    # EXECUTE TOOL

    tool_result = execute_tool(
        tool_name=tool,
        query=query
    )

    return {
        "tool": tool,
        "context": tool_result
    }