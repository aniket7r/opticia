"""Session message handlers."""

import logging
import time
from typing import Any

from app.services.admin.metrics_collector import metrics_collector
from app.ws.connection import ConnectionState

logger = logging.getLogger(__name__)


async def handle_session_start(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle session.start message."""
    state.mode = payload.get("mode", "voice")
    state.is_active = True
    state.start_time = time.time()

    logger.info(f"Session started: {state.session_id}, mode={state.mode}")

    # Record session start metric
    await metrics_collector.record_session_start(state.session_id)

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

    # Calculate session duration
    duration = 0.0
    if hasattr(state, "start_time") and state.start_time:
        duration = time.time() - state.start_time

    logger.info(f"Session ended: {state.session_id}, duration={duration:.1f}s")

    # Record session end metric
    await metrics_collector.record_session_end(state.session_id, duration)

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
