"""Gemini AI message handlers.

Architecture: All handlers use fire-and-forget sending.
A single background receive loop per session handles ALL responses.
"""

import base64
import logging
import re
from typing import Any

from app.services.admin.metrics_collector import metrics_collector
from app.services.gemini_service import gemini_service
from app.ws.connection import ConnectionState

logger = logging.getLogger(__name__)

# Pattern to detect search requests in AI text
SEARCH_PATTERN = re.compile(r'\[SEARCH:\s*(.+?)\]', re.IGNORECASE)


async def _handle_search_in_text(session: Any, state: ConnectionState, text: str) -> None:
    """Detect [SEARCH: query] in AI text, execute search, and feed results back."""
    from app.services.tools.registry import tool_registry

    match = SEARCH_PATTERN.search(text)
    if not match:
        return

    query = match.group(1).strip()
    logger.info(f"Detected search request: {query}")
    await state.send("ai.tool_call", {"name": "web_search", "args": {"query": query}})

    tool_result = await tool_registry.execute("web_search", {"query": query})
    if tool_result.success:
        result_text = f"Search results for '{query}':\n{tool_result.result}"
    else:
        result_text = f"Search failed: {tool_result.error}"

    # Send results back to Gemini as context
    await session.send_text_message(f"[Search results]: {result_text}")


async def _ensure_receive_loop(state: ConnectionState, session: Any) -> None:
    """Ensure background receive loop is running for this session.

    The receive loop forwards all Gemini responses (text, audio, tool calls)
    back to the WebSocket client.
    """
    # Accumulate text across chunks to detect search patterns
    turn_text_buffer: list[str] = []

    async def response_callback(chunk: dict[str, Any]) -> None:
        chunk_type = chunk.get("type")
        if chunk_type == "text":
            content = chunk["content"]
            turn_text_buffer.append(content)
            await state.send("ai.text", {
                "content": content,
                "complete": chunk.get("complete", False),
            })
        elif chunk_type == "turn_complete":
            # Check accumulated text for search requests
            full_text = "".join(turn_text_buffer)
            turn_text_buffer.clear()
            if "[SEARCH:" in full_text.upper():
                await _handle_search_in_text(session, state, full_text)
            # Notify frontend that the AI turn is complete
            await state.send("ai.turn_complete", {})
        elif chunk_type == "audio":
            await state.send("ai.audio", {
                "data": chunk["data"],
                "sampleRate": chunk.get("sampleRate", 24000),
            })
        elif chunk_type == "input_transcription":
            await state.send("user.transcription", {
                "content": chunk["content"],
            })
        elif chunk_type == "tool_call":
            await metrics_collector.record_tool_call(state.session_id, chunk["name"])
            await state.send("ai.tool_call", {
                "name": chunk["name"],
                "args": chunk["args"],
            })
        elif chunk_type == "error":
            await state.send_error("ai_error", chunk.get("message", "Unknown error"))

    await session.start_receive_loop(response_callback)


async def _get_or_create_session(state: ConnectionState, mode: str | None = None):
    """Get existing session or create a new one, with receive loop."""
    session = gemini_service.get_session(state.session_id)
    if not session:
        session_mode = mode or state.mode
        logger.info(f"Creating new Gemini session for {state.session_id}, mode={session_mode}")
        session = await gemini_service.create_session(state.session_id, session_mode)
        logger.info(f"Gemini session created for {state.session_id}")

    # Check if we need to reconnect
    if session.should_reconnect:
        await state.send("session.reconnecting", {"timeRemaining": session.time_remaining})
        session = await gemini_service.reconnect_session(state.session_id)
        if not session:
            await state.send_error("reconnect_failed", "Failed to reconnect session")
            return None
        await state.send("session.reconnected", {})

    # Ensure receive loop is running
    await _ensure_receive_loop(state, session)
    return session


async def handle_text_message(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle text.send message - send text to Gemini (fire-and-forget).

    When a video frame is included (camera active + text input), the frame
    is sent inline with the text so Gemini sees them in the same turn.
    Extra burst frames refresh the model's visual context to prevent stale references.
    """
    content = payload.get("content", "")
    frame_b64 = payload.get("frame")  # Optional: current camera frame
    if not content:
        await state.send_error("empty_content", "Text content is required")
        return

    try:
        session = await _get_or_create_session(state)
        if not session:
            return

        # Fire-and-forget: responses come via the background receive loop
        await session.send_text_message(content, frame_b64=frame_b64)
    except Exception as e:
        error_msg = str(e) if str(e) else "Unknown Gemini error"
        logger.error(f"Gemini error for {state.session_id}: {error_msg}", exc_info=True)
        await metrics_collector.record_error(
            state.session_id, "gemini_error", error_msg[:200]
        )
        await state.send_error("ai_error", error_msg[:500])


async def handle_audio_chunk(state: ConnectionState, payload: dict[str, Any]) -> None:
    """Handle audio.chunk message - stream audio to Gemini (fire-and-forget).

    Audio format: 16-bit PCM, 16kHz, mono (per Gemini Live API docs).
    Audio chunks are sent immediately without waiting for responses.
    """
    audio_b64 = payload.get("data", "")
    if not audio_b64:
        await state.send_error("empty_audio", "Audio data is required")
        return

    try:
        session = await _get_or_create_session(state, mode="voice")
        if not session:
            return

        # Fire-and-forget: decode and send audio chunk
        audio_data = base64.b64decode(audio_b64)
        await session.send_audio_chunk(audio_data)
    except Exception as e:
        error_msg = str(e) if str(e) else "Unknown Gemini audio error"
        logger.error(f"Gemini audio error for {state.session_id}: {error_msg}", exc_info=True)
        await metrics_collector.record_error(
            state.session_id, "gemini_audio_error", error_msg[:200]
        )
        await state.send_error("ai_error", error_msg[:500])


async def handle_thinking_request(
    state: ConnectionState, payload: dict[str, Any]
) -> None:
    """Handle thinking.show message - request visible reasoning."""
    # Gemini's thinking is embedded in responses
    # This handler acknowledges the preference
    await state.send("thinking.enabled", {"visible": True})
