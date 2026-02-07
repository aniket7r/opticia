"""WebSocket connection manager."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

from app.models.websocket import WSMessage


class ConnectionState:
    """State for a single WebSocket connection."""

    def __init__(self, websocket: WebSocket, session_id: str) -> None:
        self.websocket = websocket
        self.session_id = session_id
        self.connected_at = datetime.now(timezone.utc)
        self.mode: str = "voice"  # voice or text
        self.is_authenticated = False
        self.is_active = False

    async def send(self, msg_type: str, payload: dict[str, Any] | None = None) -> None:
        """Send a message to this connection."""
        message = WSMessage(
            type=msg_type,
            session_id=self.session_id,
            payload=payload or {},
        )
        await self.websocket.send_json(message.model_dump(by_alias=True))

    async def send_error(
        self, code: str, message: str, recoverable: bool = True
    ) -> None:
        """Send an error message."""
        await self.send(
            "error",
            {"code": code, "message": message, "recoverable": recoverable},
        )


class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(self) -> None:
        self.connections: dict[str, ConnectionState] = {}

    async def connect(self, websocket: WebSocket) -> ConnectionState:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        session_id = str(uuid.uuid4())
        state = ConnectionState(websocket, session_id)
        self.connections[session_id] = state
        return state

    async def disconnect(self, session_id: str) -> None:
        """Remove a connection."""
        if session_id in self.connections:
            del self.connections[session_id]

    def get(self, session_id: str) -> ConnectionState | None:
        """Get connection state by session ID."""
        return self.connections.get(session_id)

    @property
    def active_count(self) -> int:
        """Number of active connections."""
        return len(self.connections)


# Global connection manager
manager = ConnectionManager()
