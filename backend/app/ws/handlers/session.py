"""Session message handlers."""

import logging
from typing import Any

from app.ws.connection import ConnectionState

logger = logging.getLogger(__name__)


async def handle_session_start(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle session.start message."""
    state.mode = payload.get("mode", "voice")
    state.is_active = True

    logger.info(f"Session started: {state.session_id}, mode={state.mode}")

    await state.send(
        "session.ready",
        {
            "sessionId": state.session_id,
            "capabilities": ["voice", "text", "vision"],
            "mode": state.mode,
        },
    )


async def handle_session_end(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle session.end message."""
    state.is_active = False
    logger.info(f"Session ended: {state.session_id}")

    await state.send("session.ended", {"sessionId": state.session_id})


async def handle_mode_switch(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle mode.switch message."""
    new_mode = payload.get("mode", "voice")
    old_mode = state.mode
    state.mode = new_mode

    logger.info(f"Mode switched: {state.session_id}, {old_mode} -> {new_mode}")

    await state.send(
        "mode.switched",
        {"previousMode": old_mode, "currentMode": new_mode},
    )
