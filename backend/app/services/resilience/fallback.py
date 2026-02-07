"""Graceful degradation fallback chain.

Fallback chain: Video → Photo → Text
"""

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MediaMode(str, Enum):
    """Current media mode."""

    VIDEO = "video"
    PHOTO = "photo"
    TEXT = "text"


class FallbackState(BaseModel):
    """Current fallback state for a session."""

    current_mode: MediaMode = MediaMode.VIDEO
    video_available: bool = True
    audio_available: bool = True
    fallback_count: int = 0
    last_fallback_reason: str | None = None


class FallbackManager:
    """Manages fallback state and transitions."""

    def __init__(self) -> None:
        self.sessions: dict[str, FallbackState] = {}

    def get_state(self, session_id: str) -> FallbackState:
        """Get fallback state for a session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = FallbackState()
        return self.sessions[session_id]

    def trigger_video_fallback(
        self, session_id: str, reason: str = "video_failure"
    ) -> dict[str, Any]:
        """Trigger fallback from video to photo mode.

        Returns event data to send to frontend.
        """
        state = self.get_state(session_id)

        if state.current_mode == MediaMode.VIDEO:
            state.current_mode = MediaMode.PHOTO
            state.video_available = False
            state.fallback_count += 1
            state.last_fallback_reason = reason

            logger.info(f"Video fallback triggered: {session_id}, reason={reason}")

            return {
                "type": "fallback.activated",
                "payload": {
                    "from": "video",
                    "to": "photo",
                    "reason": reason,
                    "message": "Switched to photo mode for better stability",
                    "canRecover": True,
                },
            }

        return {"type": "fallback.nochange", "payload": {"currentMode": state.current_mode}}

    def trigger_photo_fallback(
        self, session_id: str, reason: str = "photo_failure"
    ) -> dict[str, Any]:
        """Trigger fallback from photo to text mode."""
        state = self.get_state(session_id)

        if state.current_mode in (MediaMode.VIDEO, MediaMode.PHOTO):
            state.current_mode = MediaMode.TEXT
            state.video_available = False
            state.fallback_count += 1
            state.last_fallback_reason = reason

            logger.info(f"Photo fallback triggered: {session_id}, reason={reason}")

            return {
                "type": "fallback.activated",
                "payload": {
                    "from": "photo",
                    "to": "text",
                    "reason": reason,
                    "message": "Switched to text mode. You can describe what you see.",
                    "canRecover": False,
                },
            }

        return {"type": "fallback.nochange", "payload": {"currentMode": state.current_mode}}

    def trigger_audio_fallback(
        self, session_id: str, reason: str = "audio_failure"
    ) -> dict[str, Any]:
        """Trigger fallback from audio to text I/O."""
        state = self.get_state(session_id)

        if state.audio_available:
            state.audio_available = False
            state.fallback_count += 1
            state.last_fallback_reason = reason

            logger.info(f"Audio fallback triggered: {session_id}, reason={reason}")

            return {
                "type": "fallback.audio",
                "payload": {
                    "reason": reason,
                    "message": "Voice unavailable. Using text input/output.",
                    "audioEnabled": False,
                },
            }

        return {"type": "fallback.nochange", "payload": {"audioEnabled": False}}

    def try_recover(self, session_id: str, mode: MediaMode) -> dict[str, Any]:
        """Attempt to recover to a higher-quality mode."""
        state = self.get_state(session_id)

        if mode == MediaMode.VIDEO and state.current_mode != MediaMode.VIDEO:
            state.current_mode = MediaMode.VIDEO
            state.video_available = True

            logger.info(f"Recovered to video mode: {session_id}")

            return {
                "type": "fallback.recovered",
                "payload": {
                    "mode": "video",
                    "message": "Video streaming restored",
                },
            }

        if mode == MediaMode.PHOTO and state.current_mode == MediaMode.TEXT:
            state.current_mode = MediaMode.PHOTO

            logger.info(f"Recovered to photo mode: {session_id}")

            return {
                "type": "fallback.recovered",
                "payload": {
                    "mode": "photo",
                    "message": "Photo capture restored",
                },
            }

        return {"type": "fallback.nochange", "payload": {}}

    def cleanup(self, session_id: str) -> None:
        """Cleanup state for a session."""
        self.sessions.pop(session_id, None)


# Singleton instance
fallback_manager = FallbackManager()
