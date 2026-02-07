"""Tool registry with fixed alphabetical ordering.

Follows Manus context engineering patterns:
- Tools registered with consistent prefixes (vision_, web_, etc.)
- Fixed alphabetical ordering preserves KV-cache
- Tool masking via enabled/disabled flags (never remove tools)
"""

import logging
from typing import Any, Callable, Coroutine

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    """Definition of a tool for Gemini."""

    name: str
    description: str
    parameters: dict[str, Any]
    enabled: bool = True


class ToolResult(BaseModel):
    """Result from tool execution."""

    tool_name: str
    success: bool
    result: Any
    error: str | None = None


# Type for async tool handlers
ToolHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, ToolResult]]


class ToolRegistry:
    """Registry for all available tools.

    Key principles (Manus patterns):
    - Never remove tools mid-session (invalidates cache)
    - Use masking via enabled flag instead
    - Fixed alphabetical ordering for cache stability
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: ToolHandler,
    ) -> None:
        """Register a tool with its handler."""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
        )
        self._handlers[name] = handler
        logger.info(f"Registered tool: {name}")

    def get_definitions(self, include_disabled: bool = True) -> list[dict[str, Any]]:
        """Get tool definitions in fixed alphabetical order.

        Always include all tools (even disabled) to preserve cache.
        Masking happens at the logits level, not here.
        """
        sorted_names = sorted(self._tools.keys())
        definitions = []

        for name in sorted_names:
            tool = self._tools[name]
            if include_disabled or tool.enabled:
                definitions.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                })

        return definitions

    def get_gemini_tools(self) -> list[dict[str, Any]]:
        """Get tools formatted for Gemini API."""
        definitions = self.get_definitions()
        return [
            {
                "function_declarations": [
                    {
                        "name": d["name"],
                        "description": d["description"],
                        "parameters": d["parameters"],
                    }
                    for d in definitions
                ]
            }
        ]

    def mask_tool(self, name: str, enabled: bool) -> None:
        """Enable or disable a tool (masking, not removal)."""
        if name in self._tools:
            self._tools[name].enabled = enabled
            logger.info(f"Tool {name} {'enabled' if enabled else 'masked'}")

    def is_enabled(self, name: str) -> bool:
        """Check if a tool is currently enabled."""
        return self._tools.get(name, ToolDefinition(name="", description="", parameters={})).enabled

    async def execute(self, name: str, args: dict[str, Any]) -> ToolResult:
        """Execute a tool by name with given arguments."""
        if name not in self._handlers:
            return ToolResult(
                tool_name=name,
                success=False,
                result=None,
                error=f"Unknown tool: {name}",
            )

        if not self.is_enabled(name):
            return ToolResult(
                tool_name=name,
                success=False,
                result=None,
                error=f"Tool is currently disabled: {name}",
            )

        handler = self._handlers[name]
        try:
            result = await handler(args)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {name}, {e}")
            return ToolResult(
                tool_name=name,
                success=False,
                result=None,
                error=str(e),
            )

    @property
    def tool_names(self) -> list[str]:
        """Get all tool names in alphabetical order."""
        return sorted(self._tools.keys())


# Global registry instance
tool_registry = ToolRegistry()
