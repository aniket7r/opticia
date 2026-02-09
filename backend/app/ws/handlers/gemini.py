"""Gemini AI message handlers.

Architecture: All handlers use fire-and-forget sending.
A single background receive loop per session handles ALL responses.
"""

import asyncio
import base64
import json
import logging
import re
from typing import Any

from app.services.admin.metrics_collector import metrics_collector
from app.services.gemini_service import gemini_service
from app.ws.connection import ConnectionState

logger = logging.getLogger(__name__)

# Pattern to detect search requests in AI text
SEARCH_PATTERN = re.compile(r'\[SEARCH:\s*(.+?)\]', re.IGNORECASE)

# Patterns to detect task mode in AI text
TASK_PATTERN = re.compile(r'\[TASK:\s*(\{.+?\})\]', re.IGNORECASE | re.DOTALL)
TASK_UPDATE_PATTERN = re.compile(r'\[TASK_UPDATE:\s*(\{.+?\})\]', re.IGNORECASE)
TASK_COMPLETE_PATTERN = re.compile(r'\[TASK_COMPLETE\]', re.IGNORECASE)


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


def _extract_json_from_tag(text: str, tag: str) -> str | None:
    """Extract JSON object from a [TAG: {...}] pattern using bracket counting."""
    idx = text.upper().find(f"[{tag.upper()}:")
    if idx == -1:
        return None
    # Find the opening brace
    brace_start = text.find("{", idx)
    if brace_start == -1:
        return None
    # Count braces to find the matching closing brace
    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                raw = text[brace_start:i + 1]
                # Sanitize LLM-generated JSON
                raw = re.sub(r',\s*,', ',', raw)
                raw = re.sub(r',\s*\]', ']', raw)
                raw = re.sub(r',\s*\}', '}', raw)
                return raw
    return None


async def _handle_task_in_text(state: ConnectionState, text: str) -> None:
    """Detect [TASK:], [TASK_UPDATE:], [TASK_COMPLETE] patterns in AI text."""

    # Check for new task creation
    raw_json = _extract_json_from_tag(text, "TASK")
    if raw_json:
        try:
            task_json = json.loads(raw_json)
            title = task_json.get("title", "Task")
            raw_steps = task_json.get("steps", [])

            steps = []
            for i, s in enumerate(raw_steps):
                steps.append({
                    "id": f"step-{i}",
                    "title": s.get("title", f"Step {i+1}") if isinstance(s, dict) else str(s),
                    "description": s.get("description") if isinstance(s, dict) else None,
                    "status": "current" if i == 0 else "upcoming",
                    "toggleable": True,
                })

            await state.send("task.propose", {
                "id": f"task-{state.session_id[:8]}",
                "title": title,
                "steps": steps,
                "currentStep": 0,
            })
            logger.info(f"Task proposed: {title} with {len(steps)} steps")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse task JSON: {e}")
        return

    # Check for step update
    update_match = TASK_UPDATE_PATTERN.search(text)
    if update_match:
        try:
            update_json = json.loads(update_match.group(1))
            step_index = update_json.get("step", 0)
            status = update_json.get("status", "completed")
            await state.send("task.step_update", {
                "stepIndex": step_index,
                "status": status,
            })
            logger.info(f"Task step {step_index} -> {status}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse task update JSON: {e}")
        return

    # Check for task completion
    if TASK_COMPLETE_PATTERN.search(text):
        await state.send("task.complete", {})
        logger.info("Task completed")


async def _ensure_receive_loop(state: ConnectionState, session: Any) -> None:
    """Ensure background receive loop is running for this session.

    The receive loop forwards all Gemini responses (text, audio, tool calls)
    back to the WebSocket client.

    In voice mode, output_transcription may arrive AFTER turn_complete.
    We use delayed processing: if the buffer has patterns at turn_complete,
    process immediately. Otherwise, wait up to 2s for late transcription.
    """
    turn_text_buffer: list[str] = []
    pending_process: list[asyncio.Task | None] = [None]

    async def _process_buffer() -> None:
        """Process accumulated text buffer for search/task patterns."""
        full_text = "".join(turn_text_buffer)
        turn_text_buffer.clear()
        if "[SEARCH:" in full_text.upper():
            await _handle_search_in_text(session, state, full_text)
        has_task = "[TASK" in full_text.upper()
        logger.info(f"Buffer processed: {len(full_text)} chars, has_task={has_task}")
        if has_task:
            await _handle_task_in_text(state, full_text)
        await state.send("ai.turn_complete", {})

    async def _delayed_process(delay: float = 2.0) -> None:
        """Wait for late-arriving output_transcription, then process."""
        try:
            await asyncio.sleep(delay)
            await _process_buffer()
        except asyncio.CancelledError:
            pass  # Timer was cancelled (more text arrived or new turn)

    async def response_callback(chunk: dict[str, Any]) -> None:
        chunk_type = chunk.get("type")
        if chunk_type == "text":
            content = chunk["content"]
            turn_text_buffer.append(content)
            await state.send("ai.text", {
                "content": content,
                "complete": chunk.get("complete", False),
            })
            # If post-turn-complete text arrives, reset the delay timer
            if pending_process[0] and not pending_process[0].done():
                pending_process[0].cancel()
                pending_process[0] = asyncio.create_task(_delayed_process(1.5))
        elif chunk_type == "turn_complete":
            full_text = "".join(turn_text_buffer)
            has_patterns = "[TASK" in full_text.upper() or "[SEARCH:" in full_text.upper()

            if has_patterns:
                # Patterns already in buffer from part.text — process now
                await _process_buffer()
            else:
                # No patterns yet — wait for output_transcription
                logger.info(f"Turn complete: {len(full_text)} chars, delaying for transcription")
                if pending_process[0] and not pending_process[0].done():
                    pending_process[0].cancel()
                pending_process[0] = asyncio.create_task(_delayed_process(2.0))
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


async def handle_task_accept(state: ConnectionState, payload: dict[str, Any]) -> None:
    """User accepted the proposed task — activate task mode."""
    await state.send("task.start", payload)
    logger.info(f"Task accepted: {payload.get('title', 'Unknown')}")
    session = gemini_service.get_session(state.session_id)
    if session:
        await session.send_text_message(
            "[SYSTEM] User accepted the guided task. Begin guiding them step by step. "
            "When they complete each step, output [TASK_UPDATE: {\"step\": N, \"status\": \"completed\"}]. "
            "When all steps are done, output [TASK_COMPLETE]."
        )


async def handle_task_decline(state: ConnectionState, payload: dict[str, Any]) -> None:
    """User declined the proposed task — explain conversationally instead."""
    logger.info("Task declined by user")
    session = gemini_service.get_session(state.session_id)
    if session:
        await session.send_text_message(
            "[SYSTEM] User declined step-by-step guidance. "
            "Just explain the topic conversationally instead, without task steps."
        )


async def handle_task_step_done(state: ConnectionState, payload: dict[str, Any]) -> None:
    """User manually marked a step as done via checkbox."""
    step_index = payload.get("stepIndex", 0)
    logger.info(f"User marked step {step_index} as done")
    session = gemini_service.get_session(state.session_id)
    if session:
        await session.send_text_message(
            f"[SYSTEM] User completed step {step_index + 1}. "
            "Acknowledge briefly and guide them to the next step."
        )
