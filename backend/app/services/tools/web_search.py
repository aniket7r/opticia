"""Web search tool implementation.

Tool: web_search
Prefix: web_ (following Manus naming convention)
"""

import logging
from typing import Any

import httpx

from app.services.tools.registry import ToolResult, tool_registry

logger = logging.getLogger(__name__)

# Tool definition
WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for current information. Use for questions about recent events, facts, or when you need up-to-date information.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default 5, max 10)",
            },
        },
        "required": ["query"],
    },
}


async def web_search_handler(args: dict[str, Any]) -> ToolResult:
    """Execute web search and return results.

    Note: In production, integrate with a real search API
    (Google Custom Search, Bing, SerpAPI, etc.)
    """
    query = args.get("query", "")
    num_results = min(args.get("num_results", 5), 10)

    if not query:
        return ToolResult(
            tool_name="web_search",
            success=False,
            result=None,
            error="Query is required",
        )

    try:
        # TODO: Replace with actual search API
        # For hackathon MVP, use a placeholder or free search API
        results = await _perform_search(query, num_results)

        # Format results concisely (restoration strategy - keep URLs, drop full content)
        formatted = []
        for r in results:
            formatted.append({
                "title": r.get("title", ""),
                "snippet": r.get("snippet", "")[:200],  # Truncate for context efficiency
                "url": r.get("url", ""),
            })

        return ToolResult(
            tool_name="web_search",
            success=True,
            result={
                "query": query,
                "results": formatted,
                "count": len(formatted),
            },
        )
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return ToolResult(
            tool_name="web_search",
            success=False,
            result=None,
            error=str(e),
        )


async def _perform_search(query: str, num_results: int) -> list[dict[str, Any]]:
    """Perform web search using DuckDuckGo (ddgs package)."""
    from ddgs import DDGS

    try:
        results = DDGS().text(query, max_results=num_results)

        return [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        return [
            {
                "title": f"Search failed for: {query}",
                "snippet": f"Search temporarily unavailable: {str(e)[:100]}",
                "url": "",
            }
        ]


def register_web_search_tool() -> None:
    """Register the web search tool with the registry."""
    tool_registry.register(
        name=WEB_SEARCH_TOOL["name"],
        description=WEB_SEARCH_TOOL["description"],
        parameters=WEB_SEARCH_TOOL["parameters"],
        handler=web_search_handler,
    )
