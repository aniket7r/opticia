"""Tool execution handlers."""

import logging
from typing import Any

from app.services.gemini_service import gemini_service
from app.services.tools.registry import tool_registry
from app.ws.connection import ConnectionState

logger = logging.getLogger(__name__)


async def handle_tool_response(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle tool.response message - user/frontend providing tool result.

    This is called when the frontend has gathered additional info
    (e.g., focused image capture for vision_analyze).
    """
    tool_name = payload.get("toolName", "")
    tool_call_id = payload.get("toolCallId", "")
    result = payload.get("result", {})

    if not tool_name or not tool_call_id:
        await state.send_error("invalid_tool_response", "toolName and toolCallId required")
        return

    session = gemini_service.get_session(state.session_id)
    if not session or not session._session:
        await state.send_error("no_session", "No active session")
        return

    try:
        # Send tool response to Gemini
        from google.genai import types

        await session._session.send_tool_response(
            function_responses=[
                types.FunctionResponse(
                    id=tool_call_id,
                    name=tool_name,
                    response=result,
                )
            ]
        )

        # Continue receiving AI response
        async for response in session._session.receive():
            if response.server_content and response.server_content.model_turn:
                for part in response.server_content.model_turn.parts:
                    if part.text:
                        await state.send(
                            "ai.text",
                            {
                                "content": part.text,
                                "complete": response.server_content.turn_complete,
                            },
                        )

            if response.server_content and response.server_content.turn_complete:
                break

    except Exception as e:
        logger.error(f"Tool response error: {e}")
        await state.send_error("tool_response_error", str(e))


async def handle_tool_execute(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle tool.execute message - execute a tool locally.

    This is for tools that can execute server-side (web_search, deep_research).
    """
    tool_name = payload.get("toolName", "")
    args = payload.get("args", {})

    if not tool_name:
        await state.send_error("invalid_tool_execute", "toolName required")
        return

    try:
        result = await tool_registry.execute(tool_name, args)

        if result.success:
            await state.send(
                "tool.result",
                {
                    "toolName": result.tool_name,
                    "success": True,
                    "result": result.result,
                },
            )
        else:
            await state.send(
                "tool.result",
                {
                    "toolName": result.tool_name,
                    "success": False,
                    "error": result.error,
                },
            )
    except Exception as e:
        logger.error(f"Tool execute error: {e}")
        await state.send_error("tool_execute_error", str(e))
