"""Gemini Live API service."""

import asyncio
import base64
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

# Gemini Live API constraints
SESSION_TIMEOUT_SECONDS = 120  # 2-minute limit
RECONNECT_BUFFER_SECONDS = 10  # Reconnect before timeout


class GeminiSession:
    """Manages a single Gemini Live API session."""

    def __init__(self, session_id: str, mode: str = "voice") -> None:
        self.session_id = session_id
        self.mode = mode
        self.started_at: datetime | None = None
        self.context_history: list[dict[str, Any]] = []
        self.tool_call_count = 0
        self.running_summary = ""
        self._client: genai.Client | None = None
        self._live_session: Any = None
        self._is_active = False

    @property
    def time_remaining(self) -> float:
        """Seconds remaining before session timeout."""
        if not self.started_at:
            return SESSION_TIMEOUT_SECONDS
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return max(0, SESSION_TIMEOUT_SECONDS - elapsed)

    @property
    def should_reconnect(self) -> bool:
        """Check if session should reconnect soon."""
        return self.time_remaining < RECONNECT_BUFFER_SECONDS

    def _build_system_prompt(self) -> str:
        """Build stable system prompt for KV-cache optimization."""
        # Static prefix - never include timestamps
        return """You are Opticia AI, a helpful visual assistant that can see through the user's camera and guide them with voice or text.

## Core Capabilities
- Real-time visual understanding through camera feed
- Step-by-step guidance for tasks
- Voice conversation with natural responses
- Text alternative when voice isn't available

## Interaction Style
- Be concise but friendly
- Ask clarifying questions when needed
- Provide clear, actionable guidance
- Show your reasoning when solving problems

## Safety Rules
- Never provide medical, legal, or financial advice without disclaimers
- Recommend professional help for serious matters
- Be transparent about limitations
- Respect user privacy - don't store or share visual data"""

    async def start(self) -> None:
        """Start a new Gemini Live session."""
        self._client = genai.Client(api_key=settings.gemini_api_key)

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO", "TEXT"] if self.mode == "voice" else ["TEXT"],
            system_instruction=self._build_system_prompt(),
        )

        self._live_session = self._client.aio.live.connect(
            model="gemini-2.0-flash-exp",
            config=config,
        )

        self.started_at = datetime.now(timezone.utc)
        self._is_active = True
        logger.info(f"Gemini session started: {self.session_id}")

    async def send_text(self, text: str) -> AsyncGenerator[dict[str, Any], None]:
        """Send text and stream response."""
        if not self._live_session or not self._is_active:
            raise RuntimeError("Session not active")

        async with self._live_session as session:
            await session.send(input=text, end_of_turn=True)

            async for response in session.receive():
                if response.text:
                    yield {
                        "type": "text",
                        "content": response.text,
                        "complete": response.server_content.turn_complete
                        if response.server_content
                        else False,
                    }

                # Handle tool calls
                if response.tool_call:
                    self.tool_call_count += 1
                    yield {
                        "type": "tool_call",
                        "name": response.tool_call.function_calls[0].name
                        if response.tool_call.function_calls
                        else None,
                        "args": response.tool_call.function_calls[0].args
                        if response.tool_call.function_calls
                        else {},
                    }

                    # Attention recitation every 5 tool calls
                    if self.tool_call_count % 5 == 0:
                        await self._recite_attention(session)

        # Append to context history (append-only for cache)
        self.context_history.append({"role": "user", "content": text})

    async def send_audio(
        self, audio_data: bytes, sample_rate: int = 16000
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Send audio and stream response."""
        if not self._live_session or not self._is_active:
            raise RuntimeError("Session not active")

        async with self._live_session as session:
            # Send audio as base64
            audio_b64 = base64.b64encode(audio_data).decode()
            await session.send(
                input=types.LiveClientRealtimeInput(
                    media_chunks=[
                        types.Blob(mime_type="audio/pcm", data=audio_b64)
                    ]
                )
            )

            async for response in session.receive():
                if response.text:
                    yield {"type": "text", "content": response.text}

                if response.data:
                    yield {
                        "type": "audio",
                        "data": base64.b64encode(response.data).decode(),
                        "format": "pcm16",
                    }

    async def send_image(
        self,
        image_b64: str,
        mime_type: str = "image/jpeg",
        source: str = "camera",
        prompt: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Send image frame and stream response."""
        if not self._live_session or not self._is_active:
            raise RuntimeError("Session not active")

        async with self._live_session as session:
            # Build context for the image
            context = f"[Visual input from {source}]"
            if prompt:
                context = f"{context} {prompt}"

            # Send image as blob
            await session.send(
                input=types.LiveClientRealtimeInput(
                    media_chunks=[
                        types.Blob(mime_type=mime_type, data=image_b64)
                    ]
                )
            )

            # Also send context message
            await session.send(input=context, end_of_turn=True)

            async for response in session.receive():
                if response.text:
                    yield {
                        "type": "text",
                        "content": response.text,
                        "complete": response.server_content.turn_complete
                        if response.server_content
                        else False,
                    }

                # Check for camera repositioning requests in response
                if response.text and "move" in response.text.lower() and "camera" in response.text.lower():
                    yield {
                        "type": "vision_request",
                        "action": "reposition",
                        "description": response.text,
                    }

        # Append to context history
        self.context_history.append({"role": "user", "content": f"[{source} image]"})

    async def _recite_attention(self, session: Any) -> None:
        """Recite running summary to prevent goal drift."""
        if self.running_summary:
            await session.send(
                input=f"[ATTENTION RECITATION]\nCurrent objective: {self.running_summary}",
                end_of_turn=False,
            )

    def update_summary(self, summary: str) -> None:
        """Update running summary for attention recitation."""
        self.running_summary = summary

    def serialize_context(self) -> dict[str, Any]:
        """Serialize context for session handoff."""
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "context_history": self.context_history,
            "tool_call_count": self.tool_call_count,
            "running_summary": self.running_summary,
        }

    @classmethod
    def restore_context(cls, data: dict[str, Any]) -> "GeminiSession":
        """Restore session from serialized context."""
        session = cls(data["session_id"], data["mode"])
        session.context_history = data.get("context_history", [])
        session.tool_call_count = data.get("tool_call_count", 0)
        session.running_summary = data.get("running_summary", "")
        return session

    async def close(self) -> None:
        """Close the session."""
        self._is_active = False
        if self._live_session:
            # Cleanup will happen automatically
            pass
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
