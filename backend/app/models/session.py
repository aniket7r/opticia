"""Session models."""

from datetime import datetime
from typing import Literal

from app.models.base import BaseSchema


class SessionCreate(BaseSchema):
    """Request to create a new session."""

    pass


class Session(BaseSchema):
    """Session metadata."""

    id: str
    created_at: datetime
    ended_at: datetime | None = None
    status: Literal["active", "ended", "error"] = "active"
    tool_calls_count: int = 0
    fallback_activations: int = 0
    total_tokens: int = 0


class SessionUpdate(BaseSchema):
    """Request to update session."""

    status: Literal["active", "ended", "error"] | None = None
    tool_calls_count: int | None = None
    fallback_activations: int | None = None
    total_tokens: int | None = None
