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

# Pattern to detect report generation requests
REPORT_PATTERN = re.compile(r'\[REPORT:\s*(.+?)\]', re.IGNORECASE)


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


def _sanitize_json(raw: str) -> str:
    """Aggressively sanitize LLM/voice-transcribed JSON."""
    # Replace smart/curly quotes with straight quotes
    raw = raw.replace('\u201c', '"').replace('\u201d', '"')
    raw = raw.replace('\u2018', "'").replace('\u2019', "'")
    # Replace single quotes used as JSON delimiters with double quotes
    # (common in voice transcription)
    raw = re.sub(r"(?<=[\[{,:])\s*'", ' "', raw)
    raw = re.sub(r"'\s*(?=[\]},:}])", '"', raw)
    # Fix unquoted keys: {title: "..." } -> {"title": "..."}
    raw = re.sub(r'(?<=[{,])\s*(\w+)\s*:', r' "\1":', raw)
    # Remove double commas, trailing commas
    raw = re.sub(r',\s*,', ',', raw)
    raw = re.sub(r',\s*\]', ']', raw)
    raw = re.sub(r',\s*\}', '}', raw)
    # Remove newlines/tabs inside the JSON
    raw = raw.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    # Collapse multiple spaces
    raw = re.sub(r' {2,}', ' ', raw)
    return raw


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
                raw = _sanitize_json(raw)
                logger.info(f"Extracted JSON from [{tag}]: {raw[:300]}")
                return raw
    return None


def _parse_task_json_with_fallback(raw_json: str) -> dict | None:
    """Try to parse task JSON, with aggressive fallbacks for voice transcription."""
    # Attempt 1: strict JSON parse
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        logger.info(f"Strict JSON parse failed: {e}. Raw: {raw_json[:200]}")

    # Attempt 2: fix common voice-transcription issues and retry
    fixed = raw_json
    # Voice might transcribe "steps" array items as plain strings without braces
    # e.g., "steps": ["Step 1", "Step 2"] instead of [{"title": "Step 1"}]
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Attempt 3: regex-based extraction as last resort
    logger.info("Falling back to regex-based task extraction")
    try:
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', raw_json)
        title = title_match.group(1) if title_match else "Task"

        # Find all step titles - look for {"title": "..."} patterns
        step_titles = re.findall(r'"title"\s*:\s*"([^"]+)"', raw_json)
        # First match is the task title, rest are step titles
        if step_titles and step_titles[0] == title:
            step_titles = step_titles[1:]

        if not step_titles:
            # Try to find string array items: ["Step 1", "Step 2"]
            step_titles = re.findall(r'(?<=[\[,])\s*"([^"]{3,})"', raw_json)
            # Filter out the title and key names
            step_titles = [s for s in step_titles if s != title and s not in ("title", "steps", "description")]

        if step_titles:
            return {"title": title, "steps": [{"title": s} for s in step_titles]}
    except Exception as e:
        logger.warning(f"Regex fallback also failed: {e}")

    return None


async def _handle_task_in_text(session: Any, state: ConnectionState, text: str) -> None:
    """Detect [TASK:], [TASK_UPDATE:], [TASK_COMPLETE] patterns in AI text.

    Updates both the frontend (via WebSocket) and the session's active_task
    so context is preserved across reconnects.
    """

    # Check for new task creation
    raw_json = _extract_json_from_tag(text, "TASK")
    if raw_json:
        task_json = _parse_task_json_with_fallback(raw_json)
        if task_json:
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

            if not steps:
                logger.warning(f"Task parsed but has no steps, skipping: {title}")
                return

            await state.send("task.start", {
                "id": f"task-{state.session_id[:8]}",
                "title": title,
                "steps": steps,
                "currentStep": 0,
            })
            # Track task state in session for context preservation
            session.set_active_task(title, steps)
            logger.info(f"Task started: {title} with {len(steps)} steps")
        else:
            logger.warning(f"Could not parse task JSON even with fallbacks: {raw_json[:200]}")
        return

    # Check for step update
    raw_update = _extract_json_from_tag(text, "TASK_UPDATE")
    if raw_update:
        step_index = None
        status = "completed"
        try:
            update_json = json.loads(raw_update)
            step_index = update_json.get("step", 0)
            status = update_json.get("status", "completed")
        except json.JSONDecodeError:
            # Regex fallback: extract step number
            step_match = re.search(r'"?step"?\s*:\s*(\d+)', raw_update)
            if step_match:
                step_index = int(step_match.group(1))
            logger.info(f"TASK_UPDATE JSON fallback, step={step_index}")
        if step_index is not None:
            await state.send("task.step_update", {
                "stepIndex": step_index,
                "status": status,
            })
            # Track step progress in session
            session.update_task_step(step_index, status)
            logger.info(f"Task step {step_index} -> {status}")
        return

    # Check for task completion
    if TASK_COMPLETE_PATTERN.search(text):
        await state.send("task.complete", {})
        session.clear_active_task()
        logger.info("Task completed")


async def _handle_report_in_text(session: Any, state: ConnectionState, text: str) -> None:
    """Detect [REPORT: topic] in AI text and spawn async report generation."""
    from app.services.report_service import generate_report

    match = REPORT_PATTERN.search(text)
    if not match:
        return

    topic = match.group(1).strip()
    if not topic:
        return

    # Check if this topic was already denied
    denied = getattr(session, "denied_report_topics", set())
    for denied_topic in denied:
        if denied_topic.lower() in topic.lower():
            logger.info(f"Report topic '{topic}' was previously denied, skipping")
            return

    import uuid
    report_id = str(uuid.uuid4())
    logger.info(f"Report requested: '{topic}' (report_id={report_id})")

    # Emit generating event to frontend
    await state.send("report.generating", {
        "reportId": report_id,
        "topic": topic,
        "estimatedSeconds": 15,
    })

    # Spawn background task for report generation (don't block live session)
    async def _generate_and_send():
        try:
            result = await generate_report(
                topic=topic,
                context_history=list(session.context_history),
                session_id=state.session_id,
            )
            await state.send("report.ready", result)
            logger.info(f"Report delivered: {report_id}")
        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            await state.send("report.error", {
                "reportId": report_id,
                "error": str(e)[:200],
                "retryable": True,
            })

    asyncio.create_task(_generate_and_send())


async def _ensure_receive_loop(state: ConnectionState, session: Any) -> None:
    """Ensure background receive loop is running for this session.

    The receive loop forwards all Gemini responses (text, audio, tool calls)
    back to the WebSocket client.

    In voice mode, output_transcription may arrive AFTER turn_complete.
    We use delayed processing: if the buffer has patterns at turn_complete,
    process immediately. Otherwise, wait up to 2s for late transcription.

    IMPORTANT: If the receive loop is already running, return early to
    avoid replacing the callback closure (which would wipe the buffers).
    This is critical in voice mode where audio.chunk calls this frequently.
    """
    # Don't replace callback if receive loop is already active
    if session._receive_task and not session._receive_task.done():
        return

    turn_text_buffer: list[str] = []
    input_transcription_buffer: list[str] = []
    pending_process: list[asyncio.Task | None] = [None]

    async def _process_buffer() -> None:
        """Process accumulated text buffer for search/task patterns."""
        full_text = "".join(turn_text_buffer)
        turn_text_buffer.clear()

        # Capture user voice transcription into context_history
        user_transcript = "".join(input_transcription_buffer).strip()
        input_transcription_buffer.clear()
        if user_transcript:
            session.context_history.append({"role": "user", "content": user_transcript})
            # Update running summary with latest user topic
            session.update_summary(user_transcript[:200])

        # Capture AI response into context_history
        if full_text.strip():
            session.context_history.append({"role": "ai", "content": full_text.strip()})
            session._trim_context_history()

        if "[SEARCH:" in full_text.upper():
            await _handle_search_in_text(session, state, full_text)
        has_task = "[TASK" in full_text.upper()
        has_report = "[REPORT:" in full_text.upper()
        logger.info(f"Buffer processed: {len(full_text)} chars, has_task={has_task}, has_report={has_report}")
        if has_task:
            await _handle_task_in_text(session, state, full_text)
        if has_report:
            await _handle_report_in_text(session, state, full_text)
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
            # Always start/reset delay timer when text arrives
            if pending_process[0] and not pending_process[0].done():
                pending_process[0].cancel()
            pending_process[0] = asyncio.create_task(_delayed_process(1.5))
        elif chunk_type == "output_transcription":
            # AI speech transcribed to text — arrives AFTER turn_complete in voice mode
            content = chunk["content"]
            turn_text_buffer.append(content)
            logger.info(f"Output transcription buffered: '{content[:60]}...'")
            await state.send("ai.text", {
                "content": content,
                "complete": chunk.get("complete", False),
            })
            # Always start/reset delay timer — even if no prior timer exists
            if pending_process[0] and not pending_process[0].done():
                pending_process[0].cancel()
            pending_process[0] = asyncio.create_task(_delayed_process(2.0))
        elif chunk_type == "turn_complete":
            full_text = "".join(turn_text_buffer)
            has_patterns = "[TASK" in full_text.upper() or "[SEARCH:" in full_text.upper() or "[REPORT:" in full_text.upper()

            if has_patterns:
                # Patterns already in buffer from part.text — process now
                await _process_buffer()
            else:
                # No patterns yet — wait for output_transcription (can be 3-5s late)
                logger.info(f"Turn complete: {len(full_text)} chars, delaying for transcription")
                if pending_process[0] and not pending_process[0].done():
                    pending_process[0].cancel()
                pending_process[0] = asyncio.create_task(_delayed_process(5.0))
        elif chunk_type == "audio":
            await state.send("ai.audio", {
                "data": chunk["data"],
                "sampleRate": chunk.get("sampleRate", 24000),
            })
        elif chunk_type == "input_transcription":
            input_transcription_buffer.append(chunk["content"])
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
        session = await _do_reconnect(state)
        if not session:
            return None

    # Ensure receive loop is running
    await _ensure_receive_loop(state, session)

    # Start proactive reconnect timer (fires even without user messages)
    if not session._reconnect_timer or session._reconnect_timer.done():
        async def _proactive_reconnect() -> None:
            await _do_reconnect(state)

        session.start_reconnect_timer(_proactive_reconnect)

    return session


async def _do_reconnect(state: ConnectionState):
    """Execute session reconnect and set up the new session."""
    await state.send("session.reconnecting", {"timeRemaining": 0})
    session = await gemini_service.reconnect_session(state.session_id)
    if not session:
        await state.send_error("reconnect_failed", "Failed to reconnect session")
        return None
    await state.send("session.reconnected", {})
    # Ensure receive loop on the new session
    await _ensure_receive_loop(state, session)

    # Start reconnect timer for the new session too
    async def _proactive_reconnect() -> None:
        await _do_reconnect(state)

    session.start_reconnect_timer(_proactive_reconnect)
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


async def handle_report_decline(state: ConnectionState, payload: dict[str, Any]) -> None:
    """User declined a report suggestion — track the topic to avoid nagging."""
    topic = payload.get("topic", "")
    logger.info(f"Report declined for topic: {topic}")
    session = gemini_service.get_session(state.session_id)
    if session and topic:
        session.denied_report_topics.add(topic.lower())


async def handle_report_decline(state: ConnectionState, payload: dict[str, Any]) -> None:
    """User declined a report suggestion — track topic to prevent nagging."""
    topic = payload.get("topic", "")
    logger.info(f"Report declined for topic: {topic}")
    session = gemini_service.get_session(state.session_id)
    if session and topic:
        session.denied_report_topics.add(topic.lower())


async def handle_task_step_done(state: ConnectionState, payload: dict[str, Any]) -> None:
    """User manually marked a step as done via checkbox."""
    step_index = payload.get("stepIndex", 0)
    logger.info(f"User marked step {step_index} as done")
    session = gemini_service.get_session(state.session_id)
    if session:
        # Track step progress in session for context preservation
        session.update_task_step(step_index, "completed")
        await session.send_text_message(
            f"[SYSTEM] User completed step {step_index + 1}. "
            "Acknowledge briefly and guide them to the next step."
        )
