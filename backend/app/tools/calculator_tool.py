import re

def calculator_tool(query: str):

    try:

        expression = re.sub(
            r"[^0-9\+\-\*\/\.\(\) ]",
            "",
            query
        )

        result = eval(expression)

        return f"The answer is {result}"

    except Exception as e:

        return f"Calculation failed: {str(e)}"