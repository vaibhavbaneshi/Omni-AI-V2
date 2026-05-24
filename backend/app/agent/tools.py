from app.agent.schemas import ToolResult


class ToolRegistry:

    def __init__(self):
        self._tools = {}

    def register(self, name: str, handler):
        self._tools[name] = handler

    def get(self, name: str):
        return self._tools[name]

    def execute(self, name: str, **kwargs) -> ToolResult:
        return self.get(name)(**kwargs)

    def names(self):
        return list(self._tools.keys())
