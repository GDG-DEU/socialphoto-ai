from __future__ import annotations

import logging
from typing import Any

from src.services.agent.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes declared tools by name and returns normalized results."""

    def __init__(self, tools: list[BaseTool]) -> None:
        """Build a lookup map of tool names to tool instances."""
        self._tool_map = {tool.name: tool for tool in tools}

    async def execute(self, tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and return its output or an error payload."""
        try:
            tool = self._tool_map.get(tool_name)
            if tool is None:
                raise ValueError(f"Unknown tool: {tool_name}")

            result = await tool.execute(**tool_args)
            if isinstance(result, dict):
                return result
            return {"result": result}
        except Exception as exc:
            logger.exception("Tool execution failed for %s", tool_name)
            return {"error": str(exc)}
