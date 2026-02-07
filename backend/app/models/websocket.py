"""WebSocket message models."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import Field

from app.models.base import BaseSchema


class WSMessage(BaseSchema):
    """WebSocket message envelope."""

    type: str  # dot.notation: session.start, audio.chunk, thinking.update
    session_id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    )
    payload: dict[str, Any] = Field(default_factory=dict)


class SessionStartPayload(BaseSchema):
    """Payload for session.start message."""

    mode: Literal["voice", "text"] = "voice"


class SessionReadyPayload(BaseSchema):
    """Payload for session.ready message."""

    session_id: str
    capabilities: list[str] = ["voice", "text", "vision"]


class ErrorPayload(BaseSchema):
    """Payload for error messages."""

    code: str
    message: str
    recoverable: bool = True


class AudioChunkPayload(BaseSchema):
    """Payload for audio.chunk messages."""

    data: str  # base64 encoded audio
    format: str = "pcm16"
    sample_rate: int = 16000


class TextPayload(BaseSchema):
    """Payload for text messages."""

    content: str


class ThinkingPayload(BaseSchema):
    """Payload for thinking.update messages."""

    step: str
    icon: str | None = None
    complete: bool = False
