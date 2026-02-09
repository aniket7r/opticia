"""Deep research tool implementation.

Tool: deep_research
Uses multiple Google Search grounded queries for comprehensive research.
"""

import logging
from typing import Any

from app.services.tools.registry import ToolResult, tool_registry
from app.services.tools.web_search import web_search_handler

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
        },
        "required": ["topic"],
    },
}


async def deep_research_handler(args: dict[str, Any]) -> ToolResult:
    """Execute deep research with multi-query Google Search."""
    topic = args.get("topic", "")
    aspects = args.get("aspects", [])

    if not topic:
        return ToolResult(
            tool_name="deep_research",
            success=False,
            result=None,
            error="Topic is required",
        )

    try:
        # Build search queries from topic + aspects
        queries = [topic]
        for aspect in aspects[:3]:
            queries.append(f"{topic} {aspect}")

        # Run searches and collect results
        answers = []
        all_sources = []

        for query in queries:
            result = await web_search_handler({"query": query})
            if result.success:
                answers.append(result.result.get("answer", ""))
                for s in result.result.get("sources", []):
                    if s.get("url") and s["url"] not in [x.get("url") for x in all_sources]:
                        all_sources.append(s)

        combined = "\n\n".join(f"[{q}]: {a}" for q, a in zip(queries, answers) if a)

        return ToolResult(
            tool_name="deep_research",
            success=True,
            result={
                "topic": topic,
                "synthesis": combined,
                "sources": all_sources[:8],
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
