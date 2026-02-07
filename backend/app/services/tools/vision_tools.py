"""Vision investigation tools.

Tools: vision_analyze, vision_direct
Prefix: vision_ (following Manus naming convention)
"""

import logging
from typing import Any

from app.services.tools.registry import ToolResult, tool_registry

logger = logging.getLogger(__name__)

# Tool definitions
VISION_ANALYZE_TOOL = {
    "name": "vision_analyze",
    "description": "Request detailed analysis of a specific area in the current view. Use when you need to focus on a particular region, read small text, or examine details.",
    "parameters": {
        "type": "object",
        "properties": {
            "region": {
                "type": "string",
                "description": "Description of the region to analyze (e.g., 'top-left corner', 'the label on the bottle', 'the text on screen')",
            },
            "analysis_type": {
                "type": "string",
                "enum": ["text", "detail", "color", "measurement"],
                "description": "Type of analysis needed",
            },
        },
        "required": ["region"],
    },
}

VISION_DIRECT_TOOL = {
    "name": "vision_direct",
    "description": "Request the user to adjust their camera angle or position. Use when you need a different view to provide better guidance.",
    "parameters": {
        "type": "object",
        "properties": {
            "instruction": {
                "type": "string",
                "description": "Natural language instruction for camera adjustment (e.g., 'Please move the camera closer to the label', 'Can you show me the back of the device?')",
            },
            "reason": {
                "type": "string",
                "description": "Brief explanation of why this view is needed",
            },
        },
        "required": ["instruction"],
    },
}


async def vision_analyze_handler(args: dict[str, Any]) -> ToolResult:
    """Handle vision analysis request.

    This triggers the frontend to capture a higher resolution
    image of the specified region for detailed analysis.
    """
    region = args.get("region", "")
    analysis_type = args.get("analysis_type", "detail")

    if not region:
        return ToolResult(
            tool_name="vision_analyze",
            success=False,
            result=None,
            error="Region description is required",
        )

    # This result will be sent to frontend to trigger focused capture
    return ToolResult(
        tool_name="vision_analyze",
        success=True,
        result={
            "action": "analyze_region",
            "region": region,
            "analysis_type": analysis_type,
            "message": f"Focusing on: {region}",
        },
    )


async def vision_direct_handler(args: dict[str, Any]) -> ToolResult:
    """Handle camera direction request.

    This sends a suggestion to the user to reposition their camera.
    """
    instruction = args.get("instruction", "")
    reason = args.get("reason", "")

    if not instruction:
        return ToolResult(
            tool_name="vision_direct",
            success=False,
            result=None,
            error="Instruction is required",
        )

    # This result will be displayed to user as a camera direction request
    return ToolResult(
        tool_name="vision_direct",
        success=True,
        result={
            "action": "camera_direction",
            "instruction": instruction,
            "reason": reason,
            "message": instruction,
        },
    )


def register_vision_tools() -> None:
    """Register vision tools with the registry."""
    tool_registry.register(
        name=VISION_ANALYZE_TOOL["name"],
        description=VISION_ANALYZE_TOOL["description"],
        parameters=VISION_ANALYZE_TOOL["parameters"],
        handler=vision_analyze_handler,
    )

    tool_registry.register(
        name=VISION_DIRECT_TOOL["name"],
        description=VISION_DIRECT_TOOL["description"],
        parameters=VISION_DIRECT_TOOL["parameters"],
        handler=vision_direct_handler,
    )
