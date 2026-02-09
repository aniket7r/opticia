"""Web search tool implementation using Gemini API with Google Search grounding.

Uses a side-channel Gemini API call (not the Live session) to perform
Google Search and return grounded results. This avoids the tool+video
incompatibility in the native audio model.
"""

import logging
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.tools.registry import ToolResult, tool_registry

logger = logging.getLogger(__name__)

# Tool definition
WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for current information using Google Search.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
        },
        "required": ["query"],
    },
}


async def web_search_handler(args: dict[str, Any]) -> ToolResult:
    """Execute web search via Gemini API with Google Search grounding."""
    query = args.get("query", "")

    if not query:
        return ToolResult(
            tool_name="web_search",
            success=False,
            result=None,
            error="Query is required",
        )

    try:
        client = genai.Client(api_key=settings.gemini_api_key)

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Search and provide a concise, factual answer: {query}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )

        answer = response.text or "No results found."

        # Extract grounding sources from metadata
        sources = []
        if (response.candidates
                and response.candidates[0].grounding_metadata
                and response.candidates[0].grounding_metadata.grounding_chunks):
            for chunk in response.candidates[0].grounding_metadata.grounding_chunks:
                if hasattr(chunk, 'web') and chunk.web:
                    sources.append({
                        "title": chunk.web.title or "",
                        "url": chunk.web.uri or "",
                    })

        return ToolResult(
            tool_name="web_search",
            success=True,
            result={
                "query": query,
                "answer": answer,
                "sources": sources[:5],
            },
        )
    except Exception as e:
        logger.error(f"Google Search error: {e}", exc_info=True)
        return ToolResult(
            tool_name="web_search",
            success=False,
            result=None,
            error=str(e)[:200],
        )


def register_web_search_tool() -> None:
    """Register the web search tool with the registry."""
    tool_registry.register(
        name=WEB_SEARCH_TOOL["name"],
        description=WEB_SEARCH_TOOL["description"],
        parameters=WEB_SEARCH_TOOL["parameters"],
        handler=web_search_handler,
    )
