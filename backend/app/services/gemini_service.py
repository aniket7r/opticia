"""Gemini Live API service.

Based on official documentation:
- https://ai.google.dev/gemini-api/docs/live
- https://googleapis.github.io/python-genai/
"""

import base64
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

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
# For Gemini Live API, use models with live/realtime support
# Options: "gemini-2.0-flash-exp", "models/gemini-2.0-flash-exp"
# See: https://ai.google.dev/gemini-api/docs/models
LIVE_API_MODEL = settings.gemini_model if hasattr(settings, 'gemini_model') and settings.gemini_model else "models/gemini-2.0-flash-exp"


class GeminiSession:
    """Manages a single Gemini Live API session.

    Uses the official google-genai SDK methods:
    - send_client_content() for text (deterministic ordering)
    - send_realtime_input() for audio/video (low-latency streaming)
    """

    def __init__(self, session_id: str, mode: str = "voice") -> None:
        self.session_id = session_id
        self.mode = mode  # "voice" or "text"
        self.has_video = False  # Track if video is being used
        self.started_at: datetime | None = None
        self.context_history: list[dict[str, Any]] = []
        self.tool_call_count = 0
        self.running_summary = ""
        self._client: genai.Client | None = None
        self._session: Any = None
        self._is_active = False

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
- Real-time visual understanding through camera feed
- Step-by-step guidance for tasks
- Voice conversation with natural responses
- Text alternative when voice isn't available

## Interaction Style
- Be concise but friendly
- Ask clarifying questions when needed
- Provide clear, actionable guidance
- Show your reasoning when solving problems"""

        return base_prompt + get_safety_prompt_addition()

    async def start(self) -> None:
        """Start a new Gemini Live session."""
        from app.services.tools.registry import tool_registry

        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        logger.info(f"Starting Gemini session with model: {LIVE_API_MODEL}")
        self._client = genai.Client(api_key=settings.gemini_api_key)

        # Per docs: Can only set ONE response modality per session
        response_modality = "AUDIO" if self.mode == "voice" else "TEXT"

        # Build tool definitions for Gemini
        tool_definitions = tool_registry.get_definitions()
        tools = None
        if tool_definitions:
            tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=t["name"],
                            description=t["description"],
                            parameters=t["parameters"],
                        )
                        for t in tool_definitions
                    ]
                )
            ]

        config = types.LiveConnectConfig(
            response_modalities=[response_modality],
            system_instruction=self._build_system_prompt(),
            tools=tools,
        )

        # Connect and enter session context
        try:
            self._session = await self._client.aio.live.connect(
                model=LIVE_API_MODEL,
                config=config,
            ).__aenter__()
        except Exception as e:
            logger.error(f"Failed to connect to Gemini Live API: {e}")
            raise RuntimeError(f"Failed to connect to Gemini: {str(e)}")

        self.started_at = datetime.now(timezone.utc)
        self._is_active = True
        logger.info(f"Gemini session started: {self.session_id}, mode={self.mode}, model={LIVE_API_MODEL}")

    async def send_text(self, text: str) -> AsyncGenerator[dict[str, Any], None]:
        """Send text using send_client_content (deterministic ordering)."""
        if not self._session or not self._is_active:
            raise RuntimeError("Session not active")

        # Use send_client_content for text (per SDK docs)
        await self._session.send_client_content(
            turns=[types.Content(parts=[types.Part(text=text)])],
            turn_complete=True,
        )

        async for response in self._session.receive():
            if response.server_content:
                # Extract text from response
                if response.server_content.model_turn:
                    for part in response.server_content.model_turn.parts:
                        if part.text:
                            yield {
                                "type": "text",
                                "content": part.text,
                                "complete": response.server_content.turn_complete,
                            }

            # Handle tool calls
            if response.tool_call:
                self.tool_call_count += 1
                for fc in response.tool_call.function_calls:
                    yield {
                        "type": "tool_call",
                        "name": fc.name,
                        "args": dict(fc.args) if fc.args else {},
                    }

                # Attention recitation every 5 tool calls (Manus pattern)
                if self.tool_call_count % 5 == 0:
                    await self._recite_attention()

            # Check if turn is complete
            if response.server_content and response.server_content.turn_complete:
                break

        # Append to context history (append-only for cache)
        self.context_history.append({"role": "user", "content": text})

    async def send_audio(self, audio_data: bytes) -> AsyncGenerator[dict[str, Any], None]:
        """Send audio using send_realtime_input (low-latency streaming).

        Audio format: 16-bit PCM, 16kHz, mono (per official docs)
        """
        if not self._session or not self._is_active:
            raise RuntimeError("Session not active")

        # Use send_realtime_input for audio (per SDK docs)
        await self._session.send_realtime_input(
            audio=types.Blob(
                mime_type="audio/pcm",
                data=base64.b64encode(audio_data).decode(),
            )
        )

        # Stream responses
        async for response in self._session.receive():
            if response.server_content and response.server_content.model_turn:
                for part in response.server_content.model_turn.parts:
                    # Text response
                    if part.text:
                        yield {"type": "text", "content": part.text}

                    # Audio response (inline_data)
                    if part.inline_data and isinstance(part.inline_data.data, bytes):
                        yield {
                            "type": "audio",
                            "data": base64.b64encode(part.inline_data.data).decode(),
                            "sampleRate": AUDIO_OUTPUT_SAMPLE_RATE,
                        }

            if response.server_content and response.server_content.turn_complete:
                break

    async def send_video_frame(
        self,
        frame_b64: str,
        mime_type: str = "image/jpeg",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Send video frame using send_realtime_input.

        Note: Video is processed at 1 FPS by Gemini.
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

        # Video frames typically don't get immediate responses
        # AI responds based on accumulated visual context
        # Yield nothing here - responses come through audio/text flow

    async def send_image(
        self,
        image_b64: str,
        mime_type: str = "image/jpeg",
        prompt: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Send a single image with optional prompt for analysis."""
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

        # If there's a prompt, send it as text
        if prompt:
            async for chunk in self.send_text(prompt):
                yield chunk
        else:
            # Request description
            async for chunk in self.send_text("What do you see in this image?"):
                yield chunk

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

    def serialize_context(self) -> dict[str, Any]:
        """Serialize context for session handoff."""
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "has_video": self.has_video,
            "context_history": self.context_history,
            "tool_call_count": self.tool_call_count,
            "running_summary": self.running_summary,
        }

    @classmethod
    def restore_context(cls, data: dict[str, Any]) -> "GeminiSession":
        """Restore session from serialized context."""
        session = cls(data["session_id"], data["mode"])
        session.has_video = data.get("has_video", False)
        session.context_history = data.get("context_history", [])
        session.tool_call_count = data.get("tool_call_count", 0)
        session.running_summary = data.get("running_summary", "")
        return session

    async def close(self) -> None:
        """Close the session."""
        self._is_active = False
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
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
        """Reconnect a session approaching timeout."""
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

        # Restore context by sending history summary
        if new_session.context_history:
            summary = f"Previous conversation summary: {len(new_session.context_history)} exchanges"
            if new_session.running_summary:
                summary += f". Current objective: {new_session.running_summary}"
            # Don't await - just prime the context
            await new_session._session.send_client_content(
                turns=[types.Content(parts=[types.Part(text=summary)])],
                turn_complete=False,
            )

        self.sessions[session_id] = new_session
        logger.info(f"Session reconnected: {session_id}")
        return new_session

    async def close_session(self, session_id: str) -> None:
        """Close and remove a session."""
        session = self.sessions.pop(session_id, None)
        if session:
            await session.close()


# Singleton instance
gemini_service = GeminiService()
