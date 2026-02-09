"""Gemini Live API service.

Based on official documentation:
- https://ai.google.dev/gemini-api/docs/live
- https://googleapis.github.io/python-genai/
"""

import asyncio
import base64
import logging
import re
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Callable, Awaitable

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

# Gemini Live API constraints (per official docs)
# Audio-only: 15 minutes, Audio+Video: 2 minutes
SESSION_TIMEOUT_AUDIO_ONLY = 900  # 15 minutes
SESSION_TIMEOUT_WITH_VIDEO = 120  # 2 minutes
RECONNECT_BUFFER_SECONDS = 15  # Reconnect before timeout

# Audio format requirements (per official docs)
# Input: 16-bit PCM, 16kHz, mono
# Output: 24kHz
AUDIO_INPUT_SAMPLE_RATE = 16000
AUDIO_OUTPUT_SAMPLE_RATE = 24000

# Model for Live API
# IMPORTANT: Do NOT include "models/" prefix - the SDK adds it automatically
# Only the native audio model supports Live API (bidiGenerateContent)
# It returns both text (thinking) and audio responses
# See: https://ai.google.dev/gemini-api/docs/models
LIVE_API_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

# Type alias for the response callback
ResponseCallback = Callable[[dict[str, Any]], Awaitable[None]]


class GeminiSession:
    """Manages a single Gemini Live API session.

    Uses the official google-genai SDK methods:
    - send_client_content() for text (deterministic ordering)
    - send_realtime_input() for audio/video (low-latency streaming)

    Architecture: A single background receive loop handles ALL responses
    from Gemini. Sending methods (text, audio, video) are fire-and-forget.
    """

    # Keep last N conversation entries for context handoff
    MAX_CONTEXT_HISTORY = 30

    def __init__(self, session_id: str, mode: str = "voice") -> None:
        self.session_id = session_id
        self.mode = mode  # "voice" or "text"
        self.has_video = False  # Track if video is being used
        self.started_at: datetime | None = None
        self.context_history: list[dict[str, Any]] = []
        self.active_task: dict[str, Any] | None = None  # {title, steps, current_step}
        self.denied_report_topics: set[str] = set()  # Topics user declined reports for
        self.tool_call_count = 0
        self.running_summary = ""
        self._client: genai.Client | None = None
        self._session: Any = None
        self._context_manager: Any = None  # Store the context manager
        self._is_active = False
        self._receive_task: asyncio.Task | None = None
        self._reconnect_timer: asyncio.Task | None = None
        self._response_callback: ResponseCallback | None = None
        self._on_reconnect_needed: Callable[[], Awaitable[None]] | None = None

    @property
    def session_timeout(self) -> int:
        """Get session timeout based on modalities used."""
        return SESSION_TIMEOUT_WITH_VIDEO if self.has_video else SESSION_TIMEOUT_AUDIO_ONLY

    @property
    def time_remaining(self) -> float:
        """Seconds remaining before session timeout."""
        if not self.started_at:
            return self.session_timeout
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return max(0, self.session_timeout - elapsed)

    @property
    def should_reconnect(self) -> bool:
        """Check if session should reconnect soon."""
        return self.time_remaining < RECONNECT_BUFFER_SECONDS

    def _build_system_prompt(self) -> str:
        """Build stable system prompt for KV-cache optimization.

        Note: Never include timestamps (invalidates cache).
        """
        from app.services.safety.layer import get_safety_prompt_addition

        base_prompt = """You are Opticia AI, a helpful visual assistant that can see through the user's camera and guide them with voice or text.

## Core Capabilities
- Real-time visual understanding through the camera feed sent to you as video frames
- Step-by-step guidance for tasks based on what you see
- Voice conversation with natural responses
- Text alternative when voice isn't available
- When the user asks you to search the web, include [SEARCH: query] in your response and the system will provide results

## Interaction Style
- Be concise but friendly
- When the user shows you something via camera, describe what you see
- IMPORTANT: Always describe what is CURRENTLY visible in the most recent frame. The user may change what they are showing between turns. Never assume the scene is the same as before - always look at the latest image.
- Ask clarifying questions when needed
- Provide clear, actionable guidance

## Task Mode (Step-by-Step Guidance)
When the user asks for step-by-step help (e.g. "how do I...", "walk me through...", "guide me"), or when you see something through the camera that requires multi-step guidance, output a structured task block in your text using this exact format:
[TASK: {"title": "Short Task Title", "steps": [{"title": "Step 1 title", "description": "Optional details"}, {"title": "Step 2 title"}, {"title": "Step 3 title"}]}]
- Only output [TASK:] ONCE at the start of your response, then continue with your normal spoken explanation
- Keep tasks to 3-8 steps with concise step titles (under 60 chars each)
- When the user says they completed a step (e.g. "done", "next", "finished that", "I did it"), output: [TASK_UPDATE: {"step": <zero-indexed step number>, "status": "completed"}]
- When you SEE through the camera that the user has completed a step (e.g. you can visually confirm they did it), PROACTIVELY output [TASK_UPDATE: {"step": N, "status": "completed"}] without waiting for them to say "done"
- CRITICAL: You MUST include [TASK_UPDATE] and [TASK_COMPLETE] as TEXT output even when you are speaking audio. The system reads these from your text output, not audio. Always output these tags as text alongside your spoken response.
- After each step is completed, briefly acknowledge it and guide the user to the next step
- When ALL steps are completed or the user wants to stop the task, output: [TASK_COMPLETE]
- If the user's camera is NOT active (no video frames being received), suggest they turn on the camera so you can visually verify their progress. Say something like "You can turn on your camera so I can see your progress."
- These tags are parsed by the system and NOT shown to the user, so always also speak your guidance naturally"""

        return base_prompt + get_safety_prompt_addition()

    async def start(self) -> None:
        """Start a new Gemini Live session."""
        from app.services.tools.registry import tool_registry

        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        # Use the native audio model for all modes
        # It's the only model that supports Live API (bidiGenerateContent)
        # It returns both text (thinking) and audio responses
        model = LIVE_API_MODEL
        # Native audio model only supports AUDIO response modality
        response_modality = "AUDIO"

        logger.info(f"Starting Gemini session with model: {model}, mode: {self.mode}, modality: {response_modality}")

        # Create client
        self._client = genai.Client(api_key=settings.gemini_api_key)

        # IMPORTANT: Custom function declaration tools break video input
        # in the native audio model. When tools are configured, the model
        # cannot process video frames. We use Google Search grounding instead
        # and handle custom tools outside the Live API session.
        # See: tools + video incompatibility in gemini-2.5-flash-native-audio

        # Build config - enable transcription to get text from audio responses
        # This allows text mode to work even though the model returns audio
        config = types.LiveConnectConfig(
            response_modalities=[response_modality],
            system_instruction=types.Content(
                parts=[types.Part(text=self._build_system_prompt())]
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

        # Connect using proper async context manager pattern
        try:
            # Create the context manager
            self._context_manager = self._client.aio.live.connect(
                model=model,
                config=config,
            )
            # Enter the context
            self._session = await self._context_manager.__aenter__()
        except Exception as e:
            logger.error(f"Failed to connect to Gemini Live API: {e}", exc_info=True)
            raise RuntimeError(f"Failed to connect to Gemini: {str(e)}")

        self.started_at = datetime.now(timezone.utc)
        self._is_active = True
        logger.info(f"Gemini session started: {self.session_id}, mode={self.mode}, model={model}")

    async def start_receive_loop(self, callback: ResponseCallback) -> None:
        """Start background receive loop that forwards all Gemini responses.

        The callback receives dicts with types: text, audio, tool_call, turn_complete, error.
        Only one receive loop runs per session.
        """
        if self._receive_task and not self._receive_task.done():
            # Already running - just update callback (for reconnect scenarios)
            self._response_callback = callback
            return
        self._response_callback = callback
        self._receive_task = asyncio.create_task(
            self._receive_loop(),
            name=f"gemini-receive-{self.session_id}",
        )

    async def _receive_loop(self) -> None:
        """Background task that receives ALL responses from Gemini.

        Handles text, audio, transcription, and tool calls.
        Tool calls are executed inline and results sent back to Gemini.

        The outer while loop re-calls receive() after each turn completes,
        since the SDK's receive() iterator ends per turn.
        """
        from app.services.tools.registry import tool_registry

        logger.info(f"Receive loop started for session {self.session_id}")
        try:
            while self._is_active and self._session:
                try:
                    async for response in self._session.receive():
                        if not self._is_active:
                            break

                        # Handle server content (text, audio, transcription)
                        if response.server_content:
                            if response.server_content.model_turn:
                                for part in response.server_content.model_turn.parts:
                                    if part.text:
                                        await self._emit({
                                            "type": "text",
                                            "content": part.text,
                                            "complete": response.server_content.turn_complete or False,
                                        })
                                    if hasattr(part, 'inline_data') and part.inline_data:
                                        audio_data = part.inline_data.data
                                        if isinstance(audio_data, bytes):
                                            audio_data = base64.b64encode(audio_data).decode()
                                        await self._emit({
                                            "type": "audio",
                                            "data": audio_data,
                                            "sampleRate": AUDIO_OUTPUT_SAMPLE_RATE,
                                        })

                            # Handle output audio transcription (AI speech → text)
                            if hasattr(response.server_content, 'output_transcription') and response.server_content.output_transcription:
                                transcription = response.server_content.output_transcription
                                if hasattr(transcription, 'text') and transcription.text:
                                    logger.info(f"Output transcription: '{transcription.text[:80]}'")
                                    await self._emit({
                                        "type": "output_transcription",
                                        "content": transcription.text,
                                        "complete": response.server_content.turn_complete or False,
                                    })

                            # Handle input audio transcription (user speech → text)
                            if hasattr(response.server_content, 'input_transcription') and response.server_content.input_transcription:
                                transcription = response.server_content.input_transcription
                                if hasattr(transcription, 'text') and transcription.text:
                                    logger.info(f"Input transcription: '{transcription.text[:80]}'")
                                    await self._emit({
                                        "type": "input_transcription",
                                        "content": transcription.text,
                                    })

                            if response.server_content.turn_complete:
                                await self._emit({"type": "turn_complete"})

                        # Handle tool calls (if tools ever re-enabled)
                        if response.tool_call:
                            self.tool_call_count += 1
                            for fc in response.tool_call.function_calls:
                                await self._emit({
                                    "type": "tool_call",
                                    "name": fc.name,
                                    "args": dict(fc.args) if fc.args else {},
                                })
                                tool_result = await tool_registry.execute(
                                    fc.name, dict(fc.args) if fc.args else {}
                                )
                                func_response = types.FunctionResponse(
                                    id=fc.id,
                                    name=fc.name,
                                    response={"result": str(tool_result.result) if tool_result.success else tool_result.error},
                                )
                                await self._session.send_tool_response(
                                    function_responses=[func_response]
                                )

                except asyncio.CancelledError:
                    raise  # Propagate cancellation
                except Exception as e:
                    if not self._is_active:
                        break
                    logger.error(f"Receive iteration error for {self.session_id}: {e}", exc_info=True)
                    await self._emit({"type": "error", "message": str(e)})
                    # Brief pause before retrying receive
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info(f"Receive loop cancelled for session {self.session_id}")
        finally:
            logger.info(f"Receive loop ended for session {self.session_id}")

    async def _emit(self, data: dict[str, Any]) -> None:
        """Emit response to the registered callback."""
        if self._response_callback:
            try:
                await self._response_callback(data)
            except Exception as e:
                logger.error(f"Error in response callback: {e}")

    async def send_text_message(self, text: str, frame_b64: str | None = None) -> None:
        """Send text to Gemini (fire-and-forget).

        Uses send_client_content() for deterministic ordering.
        When frame_b64 is provided, includes the camera frame inline
        so Gemini sees the image in the same turn as the text question.
        Responses come through the background receive loop.
        """
        if not self._session or not self._is_active:
            raise RuntimeError("Session not active")

        parts = []
        if frame_b64:
            logger.info(f"Sending text+frame to Gemini: {text[:50]}... (frame: {len(frame_b64)} chars)")
            self.has_video = True
            parts.append(types.Part(
                inline_data=types.Blob(mime_type="image/jpeg", data=frame_b64)
            ))
        else:
            logger.info(f"Sending text to Gemini: {text[:50]}...")
        parts.append(types.Part(text=text))

        await self._session.send_client_content(
            turns=[types.Content(parts=parts)],
            turn_complete=True,
        )

        self.context_history.append({"role": "user", "content": text})
        self._trim_context_history()
        # Keep running summary updated with latest user topic
        if not text.startswith("[SYSTEM]") and not text.startswith("[Search results]"):
            self.running_summary = text[:200]

    async def send_audio_chunk(self, audio_data: bytes) -> None:
        """Send audio chunk to Gemini (fire-and-forget).

        Uses send_realtime_input() for low-latency streaming.
        Audio format: 16-bit PCM, 16kHz, mono (per official docs).
        Responses come through the background receive loop.
        """
        if not self._session or not self._is_active:
            raise RuntimeError("Session not active")

        await self._session.send_realtime_input(
            audio=types.Blob(
                mime_type="audio/pcm",
                data=base64.b64encode(audio_data).decode(),
            )
        )

    async def send_video_frame(
        self,
        frame_b64: str,
        mime_type: str = "image/jpeg",
    ) -> None:
        """Send video frame using send_realtime_input.

        Note: Video is processed at 1 FPS by Gemini.
        This is fire-and-forget - responses come through the receive loop.
        """
        if not self._session or not self._is_active:
            raise RuntimeError("Session not active")

        # Mark that video is being used (affects timeout)
        self.has_video = True

        # Use send_realtime_input for video (per SDK docs)
        await self._session.send_realtime_input(
            video=types.Blob(
                mime_type=mime_type,
                data=frame_b64,
            )
        )

    async def send_image(
        self,
        image_b64: str,
        mime_type: str = "image/jpeg",
        prompt: str | None = None,
    ) -> None:
        """Send a single image with optional prompt for analysis.

        Fire-and-forget - responses come through the receive loop.
        """
        if not self._session or not self._is_active:
            raise RuntimeError("Session not active")

        self.has_video = True

        # Send image via realtime input
        await self._session.send_realtime_input(
            video=types.Blob(
                mime_type=mime_type,
                data=image_b64,
            )
        )

        # Send prompt as text
        text = prompt if prompt else "What do you see in this image?"
        await self.send_text_message(text)

    async def _recite_attention(self) -> None:
        """Recite running summary to prevent goal drift (Manus pattern)."""
        if self.running_summary and self._session:
            await self._session.send_client_content(
                turns=[types.Content(parts=[types.Part(
                    text=f"[ATTENTION RECITATION] Current objective: {self.running_summary}"
                )])],
                turn_complete=False,
            )

    def update_summary(self, summary: str) -> None:
        """Update running summary for attention recitation."""
        self.running_summary = summary

    def set_active_task(self, title: str, steps: list[dict[str, Any]]) -> None:
        """Set the active task with title and steps."""
        self.active_task = {
            "title": title,
            "steps": steps,
            "current_step": 0,
        }
        # Override running_summary with task context
        self.running_summary = f"Guiding: {title} (step 1/{len(steps)}: {steps[0].get('title', 'Step 1')})"
        logger.info(f"Active task set: {title} with {len(steps)} steps")

    def update_task_step(self, step_index: int, status: str) -> None:
        """Update a task step's status."""
        if not self.active_task:
            return
        steps = self.active_task["steps"]
        if 0 <= step_index < len(steps):
            steps[step_index]["status"] = status
            if status == "completed":
                # Find next incomplete step
                next_step = step_index + 1
                while next_step < len(steps) and steps[next_step].get("status") == "completed":
                    next_step += 1
                self.active_task["current_step"] = next_step
                # Update running summary with current progress
                completed = sum(1 for s in steps if s.get("status") == "completed")
                if next_step < len(steps):
                    self.running_summary = (
                        f"Guiding: {self.active_task['title']} "
                        f"(step {next_step + 1}/{len(steps)}: {steps[next_step].get('title', '')})"
                    )
                else:
                    self.running_summary = f"Guiding: {self.active_task['title']} (all {len(steps)} steps completed)"

    def clear_active_task(self) -> None:
        """Clear the active task (task completed or dismissed)."""
        self.active_task = None

    def _trim_context_history(self) -> None:
        """Keep context_history within limits."""
        if len(self.context_history) > self.MAX_CONTEXT_HISTORY:
            self.context_history = self.context_history[-self.MAX_CONTEXT_HISTORY:]

    def start_reconnect_timer(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Start a proactive timer that triggers reconnect before timeout.

        This ensures reconnect happens even if no user message triggers
        _get_or_create_session (e.g., user is silent watching video).
        """
        self._on_reconnect_needed = callback
        if self._reconnect_timer and not self._reconnect_timer.done():
            self._reconnect_timer.cancel()

        delay = max(0, self.session_timeout - RECONNECT_BUFFER_SECONDS)
        logger.info(f"Reconnect timer set for {delay}s (timeout={self.session_timeout}s)")
        self._reconnect_timer = asyncio.create_task(
            self._reconnect_timer_task(delay),
            name=f"reconnect-timer-{self.session_id}",
        )

    async def _reconnect_timer_task(self, delay: float) -> None:
        """Background task that triggers reconnect after delay."""
        try:
            await asyncio.sleep(delay)
            if self._is_active and self._on_reconnect_needed:
                logger.info(f"Proactive reconnect timer fired for {self.session_id}")
                await self._on_reconnect_needed()
        except asyncio.CancelledError:
            pass

    def serialize_context(self) -> dict[str, Any]:
        """Serialize context for session handoff."""
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "has_video": self.has_video,
            "context_history": self.context_history,
            "active_task": self.active_task,
            "tool_call_count": self.tool_call_count,
            "running_summary": self.running_summary,
        }

    @classmethod
    def restore_context(cls, data: dict[str, Any]) -> "GeminiSession":
        """Restore session from serialized context."""
        session = cls(data["session_id"], data["mode"])
        session.has_video = data.get("has_video", False)
        session.context_history = data.get("context_history", [])
        session.active_task = data.get("active_task")
        session.tool_call_count = data.get("tool_call_count", 0)
        session.running_summary = data.get("running_summary", "")
        return session

    async def close(self) -> None:
        """Close the session and cancel background tasks."""
        self._is_active = False

        # Cancel reconnect timer
        if self._reconnect_timer and not self._reconnect_timer.done():
            self._reconnect_timer.cancel()
            try:
                await self._reconnect_timer
            except asyncio.CancelledError:
                pass

        # Cancel receive loop
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._session:
            try:
                # Use close() method if available
                if hasattr(self._session, 'close'):
                    await self._session.close()
                # Otherwise try to exit the context manager
                elif self._context_manager:
                    await self._context_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
        logger.info(f"Gemini session closed: {self.session_id}")


class GeminiService:
    """Service for managing Gemini sessions."""

    def __init__(self) -> None:
        self.sessions: dict[str, GeminiSession] = {}

    async def create_session(self, session_id: str, mode: str = "voice") -> GeminiSession:
        """Create and start a new Gemini session."""
        session = GeminiSession(session_id, mode)
        await session.start()
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> GeminiSession | None:
        """Get an existing session."""
        return self.sessions.get(session_id)

    async def reconnect_session(self, session_id: str) -> GeminiSession | None:
        """Reconnect a session approaching timeout.

        Builds a rich context handoff from the conversation history so the
        new Gemini session knows what was being discussed and can continue
        seamlessly.
        """
        old_session = self.sessions.get(session_id)
        if not old_session:
            return None

        # Serialize context
        context_data = old_session.serialize_context()

        # Close old session
        await old_session.close()

        # Create new session with restored context
        new_session = GeminiSession.restore_context(context_data)
        await new_session.start()

        # Build rich context handoff from actual conversation history
        if new_session.context_history:
            context_msg = self._build_context_handoff(new_session)
            logger.info(f"Sending context handoff ({len(context_msg)} chars) for {session_id}")
            await new_session._session.send_client_content(
                turns=[types.Content(parts=[types.Part(text=context_msg)])],
                turn_complete=False,
            )

        self.sessions[session_id] = new_session
        logger.info(f"Session reconnected: {session_id}")
        return new_session

    def _build_context_handoff(self, session: GeminiSession) -> str:
        """Build a rich context message from conversation history.

        Includes active task state (if any) prominently at the top,
        followed by recent conversation exchanges. Truncates to stay
        within reasonable limits.
        """
        MAX_CONTEXT_CHARS = 4000  # Keep context under ~1K tokens
        MAX_ENTRY_CHARS = 500  # Truncate individual messages

        parts: list[str] = []

        parts.append("[CONTEXT HANDOFF] This is a continuation of an ongoing conversation. "
                     "The previous session timed out.")

        # Active task state — most critical for continuity
        if session.active_task:
            task = session.active_task
            title = task["title"]
            steps = task["steps"]
            current = task.get("current_step", 0)

            parts.append(f"\n[ACTIVE TASK] \"{title}\" — IN PROGRESS")
            for i, step in enumerate(steps):
                step_title = step.get("title", f"Step {i+1}")
                status = step.get("status", "upcoming")
                if status == "completed":
                    parts.append(f"  {i+1}. {step_title} ✓ DONE")
                elif i == current:
                    parts.append(f"  {i+1}. {step_title} ← CURRENT STEP")
                else:
                    parts.append(f"  {i+1}. {step_title}")

            parts.append(f"IMPORTANT: Continue guiding from step {current + 1}. "
                         "Do NOT restart the task or create a new [TASK:] block. "
                         "The task UI is already showing on the user's screen.")

        # Recent conversation history
        history = session.context_history
        if history:
            lines: list[str] = []
            total_chars = 0

            for entry in reversed(history):
                role = entry.get("role", "unknown")
                content = entry.get("content", "")
                # Strip control patterns from AI content for cleaner context
                if role == "ai":
                    content = re.sub(r'\[TASK:\s*\{.*?\}\]', '', content, flags=re.DOTALL)
                    content = re.sub(r'\[SEARCH:[^]]*\]', '', content)
                    content = re.sub(r'\[TASK_UPDATE:[^]]*\]', '', content)
                    content = re.sub(r'\[TASK_COMPLETE\]', '', content, flags=re.IGNORECASE)
                    content = re.sub(r'\[REPORT:[^]]*\]', '', content, flags=re.IGNORECASE)
                    content = content.strip()
                # Strip system messages from context
                if role == "user" and content.startswith("[SYSTEM]"):
                    continue
                if not content:
                    continue
                if len(content) > MAX_ENTRY_CHARS:
                    content = content[:MAX_ENTRY_CHARS] + "..."
                label = "User" if role == "user" else "Assistant"
                line = f"- {label}: {content}"
                if total_chars + len(line) > MAX_CONTEXT_CHARS:
                    break
                lines.append(line)
                total_chars += len(line)

            lines.reverse()
            if lines:
                parts.append("\nRecent conversation:")
                parts.extend(lines)

        if session.running_summary:
            parts.append(f"\nCurrent objective: {session.running_summary}")

        parts.append("\nContinue the conversation naturally from where we left off. "
                     "Do NOT mention the session restart to the user.")

        return "\n".join(parts)

    async def close_session(self, session_id: str) -> None:
        """Close and remove a session."""
        session = self.sessions.pop(session_id, None)
        if session:
            await session.close()


# Singleton instance
gemini_service = GeminiService()
