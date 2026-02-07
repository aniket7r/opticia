"""Gemini AI message handlers."""

import base64
import logging
from typing import Any

from app.services.admin.metrics_collector import metrics_collector
from app.services.gemini_service import gemini_service
from app.ws.connection import ConnectionState

logger = logging.getLogger(__name__)


async def handle_text_message(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle text.send message - send text to Gemini."""
    content = payload.get("content", "")
    if not content:
        await state.send_error("empty_content", "Text content is required")
        return

    session = gemini_service.get_session(state.session_id)
    if not session:
        # Create session on first message
        session = await gemini_service.create_session(state.session_id, state.mode)

    # Check if we need to reconnect
    if session.should_reconnect:
        await state.send("session.reconnecting", {})
        session = await gemini_service.reconnect_session(state.session_id)
        if not session:
            await state.send_error("reconnect_failed", "Failed to reconnect session")
            return

    try:
        # Stream response
        async for chunk in session.send_text(content):
            if chunk["type"] == "text":
                await state.send(
                    "ai.text",
                    {"content": chunk["content"], "complete": chunk.get("complete", False)},
                )
            elif chunk["type"] == "tool_call":
                # Record tool call metric
                await metrics_collector.record_tool_call(
                    state.session_id, chunk["name"]
                )
                await state.send(
                    "ai.tool_call",
                    {"name": chunk["name"], "args": chunk["args"]},
                )
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        await metrics_collector.record_error(
            state.session_id, "gemini_error", str(e)[:200]
        )
        await state.send_error("ai_error", str(e))


async def handle_audio_chunk(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle audio.chunk message - stream audio to Gemini.

    Audio format: 16-bit PCM, 16kHz, mono (per Gemini Live API docs)
    """
    audio_b64 = payload.get("data", "")
    if not audio_b64:
        await state.send_error("empty_audio", "Audio data is required")
        return

    session = gemini_service.get_session(state.session_id)
    if not session:
        session = await gemini_service.create_session(state.session_id, "voice")

    # Check if we need to reconnect
    if session.should_reconnect:
        await state.send("session.reconnecting", {"timeRemaining": session.time_remaining})
        session = await gemini_service.reconnect_session(state.session_id)
        if not session:
            await state.send_error("reconnect_failed", "Failed to reconnect session")
            return
        await state.send("session.reconnected", {})

    try:
        audio_data = base64.b64decode(audio_b64)

        async for chunk in session.send_audio(audio_data):
            if chunk["type"] == "text":
                await state.send("ai.text", {"content": chunk["content"]})
            elif chunk["type"] == "audio":
                await state.send(
                    "ai.audio",
                    {"data": chunk["data"], "sampleRate": chunk["sampleRate"]},
                )
    except Exception as e:
        logger.error(f"Gemini audio error: {e}")
        await metrics_collector.record_error(
            state.session_id, "gemini_audio_error", str(e)[:200]
        )
        await state.send_error("ai_error", str(e))


async def handle_thinking_request(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle thinking.show message - request visible reasoning."""
    # Gemini's thinking is embedded in responses
    # This handler acknowledges the preference
    await state.send("thinking.enabled", {"visible": True})
