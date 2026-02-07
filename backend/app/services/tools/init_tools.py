"""Tool initialization module.

Registers all tools with the global registry on startup.
"""

from app.services.tools.deep_research import register_deep_research_tool
from app.services.tools.registry import tool_registry
from app.services.tools.vision_tools import register_vision_tools
from app.services.tools.web_search import register_web_search_tool


def init_all_tools() -> None:
    """Initialize and register all tools.

    Call this at application startup.
    Tools are registered in alphabetical order for cache stability.
    """
    # Register tools (will be sorted alphabetically in registry)
    register_deep_research_tool()
    register_vision_tools()
    register_web_search_tool()


def get_tool_count() -> int:
    """Get number of registered tools."""
    return len(tool_registry.tool_names)
