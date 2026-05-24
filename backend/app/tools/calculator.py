import ast
import operator

from app.agent.schemas import ToolResult, timed_tool


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPERATORS:
        return ALLOWED_OPERATORS[type(node.op)](
            _eval_node(node.left),
            _eval_node(node.right)
        )

    if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPERATORS:
        return ALLOWED_OPERATORS[type(node.op)](_eval_node(node.operand))

    raise ValueError("Unsupported expression")


def calculator_tool(
    query: str,
    **_
):
    finish = timed_tool("calculator")

    try:
        expression = "".join(
            char
            for char in query
            if char in "0123456789+-*/(). "
        ).strip()

        if not expression:
            raise ValueError("No arithmetic expression found")

        parsed = ast.parse(expression, mode="eval")
        result = _eval_node(parsed.body)

        return finish(
            ToolResult(
                name="calculator",
                context=f"Calculation result: {result}",
                confidence=1,
                metadata={
                    "expression": expression,
                    "result": result
                }
            )
        )

    except Exception as error:
        return finish(
            ToolResult(
                name="calculator",
                error=str(error),
                confidence=0
            )
        )
