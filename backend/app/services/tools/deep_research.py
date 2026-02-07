"""Deep research tool implementation.

Tool: deep_research
Prefix: deep_ (following Manus naming convention)
"""

import logging
from typing import Any

from app.services.tools.registry import ToolResult, tool_registry
from app.services.tools.web_search import _perform_search

logger = logging.getLogger(__name__)

# Tool definition
DEEP_RESEARCH_TOOL = {
    "name": "deep_research",
    "description": "Perform comprehensive research on a topic using multiple sources. Use for complex questions requiring synthesis of information from various sources.",
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The research topic or question",
            },
            "aspects": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific aspects to research (optional)",
            },
            "depth": {
                "type": "string",
                "enum": ["quick", "standard", "thorough"],
                "description": "Research depth level (default: standard)",
            },
        },
        "required": ["topic"],
    },
}


async def deep_research_handler(args: dict[str, Any]) -> ToolResult:
    """Execute deep research with multi-source synthesis.

    Performs multiple searches and combines results.
    """
    topic = args.get("topic", "")
    aspects = args.get("aspects", [])
    depth = args.get("depth", "standard")

    if not topic:
        return ToolResult(
            tool_name="deep_research",
            success=False,
            result=None,
            error="Topic is required",
        )

    try:
        # Determine number of queries based on depth
        num_queries = {"quick": 2, "standard": 4, "thorough": 6}.get(depth, 4)

        # Build search queries
        queries = [topic]
        for aspect in aspects[:num_queries - 1]:
            queries.append(f"{topic} {aspect}")

        # Perform multiple searches
        all_results = []
        sources = []

        for query in queries[:num_queries]:
            results = await _perform_search(query, num_results=3)
            for r in results:
                if r.get("url") not in sources:
                    sources.append(r.get("url"))
                    all_results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("snippet", "")[:150],
                        "url": r.get("url", ""),
                        "query": query,
                    })

        # Return synthesized results
        return ToolResult(
            tool_name="deep_research",
            success=True,
            result={
                "topic": topic,
                "depth": depth,
                "sources_count": len(sources),
                "findings": all_results[:10],  # Limit for context efficiency
                "sources": sources[:10],
            },
        )
    except Exception as e:
        logger.error(f"Deep research error: {e}")
        return ToolResult(
            tool_name="deep_research",
            success=False,
            result=None,
            error=str(e),
        )


def register_deep_research_tool() -> None:
    """Register the deep research tool with the registry."""
    tool_registry.register(
        name=DEEP_RESEARCH_TOOL["name"],
        description=DEEP_RESEARCH_TOOL["description"],
        parameters=DEEP_RESEARCH_TOOL["parameters"],
        handler=deep_research_handler,
    )
