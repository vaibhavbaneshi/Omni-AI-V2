from app.tools.calculator_tool import (
    calculator_tool
)

from app.tools.web_search_tool import (
    web_search_tool
)

from app.tools.rag_tool import (
    rag_tool
)

def execute_tool(
    tool_name,
    query
):

    if tool_name == "calculator":

        return calculator_tool(query)

    elif tool_name == "web_search":

        return web_search_tool(query)

    elif tool_name == "rag":

        return rag_tool(query)

    return "No tool found"