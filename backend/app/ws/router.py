"""WebSocket routing and main handler."""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.gemini_service import gemini_service
from app.ws.connection import ConnectionState, manager
from app.ws.handlers.gemini import (
    handle_audio_chunk,
    handle_report_decline,
    handle_task_accept,
    handle_task_decline,
    handle_task_step_done,
    handle_text_message,
    handle_thinking_request,
)
from app.ws.handlers.session import (
    handle_mode_switch,
    handle_session_end,
    handle_session_start,
)
from app.ws.handlers.vision import (
    handle_mode_switch_video,
    handle_photo_capture,
    handle_video_frame,
)
from app.ws.handlers.tools import (
    handle_tool_execute,
    handle_tool_response,
)
from app.ws.handlers.resilience import (
    handle_conversation_new,
    handle_fallback_recover,
    handle_fallback_trigger,
    handle_network_ping,
    handle_network_stats,
    handle_preferences_get,
    handle_preferences_update,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Message type to handler mapping
MESSAGE_HANDLERS: dict[str, Any] = {
    # Session lifecycle
    "session.start": handle_session_start,
    "session.end": handle_session_end,
    "mode.switch": handle_mode_switch,
    # AI communication
    "text.send": handle_text_message,
    "audio.chunk": handle_audio_chunk,
    "thinking.show": handle_thinking_request,
    # Vision
    "video.frame": handle_video_frame,
    "photo.capture": handle_photo_capture,
    "video.modeSwitch": handle_mode_switch_video,
    # Tools
    "tool.execute": handle_tool_execute,
    "tool.response": handle_tool_response,
    # Preferences
    "preferences.get": handle_preferences_get,
    "preferences.update": handle_preferences_update,
    # Fallback & Resilience
    "fallback.trigger": handle_fallback_trigger,
    "fallback.recover": handle_fallback_recover,
    "network.ping": handle_network_ping,
    "network.stats": handle_network_stats,
    # Task mode
    "task.accept": handle_task_accept,
    "task.decline": handle_task_decline,
    "task.step_done": handle_task_step_done,
    # Report
    "report.decline": handle_report_decline,
    # Conversation
    "conversation.new": handle_conversation_new,
}


async def route_message(state: ConnectionState, data: dict[str, Any]) -> None:
    """Route incoming message to appropriate handler."""
    msg_type = data.get("type", "")
    payload = data.get("payload", {})

    handler = MESSAGE_HANDLERS.get(msg_type)
    if handler:
        await handler(state, payload)
    else:
        logger.warning(f"Unknown message type: {msg_type}")
        await state.send_error(
            code="unknown_message_type",
            message=f"Unknown message type: {msg_type}",
            recoverable=True,
        )


@router.websocket("/ws/session")
async def websocket_session(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for sessions."""
    state = await manager.connect(websocket)
    logger.info(f"WebSocket connected: {state.session_id}")

    try:
        # Send connection confirmation
        await state.send(
            "connection.established",
            {"sessionId": state.session_id},
        )

        # Message loop
        while True:
            data = await websocket.receive_json()
            await route_message(state, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {state.session_id}")
    except Exception as e:
        error_msg = str(e) if str(e) else "Unknown error"
        logger.error(f"WebSocket error for {state.session_id}: {error_msg}", exc_info=True)
        try:
            # Send more detailed error to client for debugging
            await state.send_error(
                code="internal_error",
                message=f"Internal error: {error_msg[:200]}",
                recoverable=False,
            )
        except Exception:
            pass  # Connection already closed
    finally:
        # Cleanup all session state
        from app.services.resilience.fallback import fallback_manager
        from app.services.resilience.network import network_monitor

        await gemini_service.close_session(state.session_id)
        fallback_manager.cleanup(state.session_id)
        network_monitor.cleanup(state.session_id)
        await manager.disconnect(state.session_id)
