"""WebSocket routing and main handler."""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.connection import ConnectionState, manager
from app.ws.handlers.session import (
    handle_mode_switch,
    handle_session_end,
    handle_session_start,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Message type to handler mapping
MESSAGE_HANDLERS: dict[str, Any] = {
    "session.start": handle_session_start,
    "session.end": handle_session_end,
    "mode.switch": handle_mode_switch,
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
        logger.error(f"WebSocket error: {state.session_id}, {e}")
        await state.send_error(
            code="internal_error",
            message="An internal error occurred",
            recoverable=False,
        )
    finally:
        await manager.disconnect(state.session_id)
