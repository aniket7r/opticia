"""Session management service."""

from datetime import datetime, timezone

from app.core.supabase import get_supabase_client
from app.models.session import Session, SessionUpdate


class SessionService:
    """Service for managing session lifecycle."""

    def __init__(self) -> None:
        self.client = get_supabase_client()
        self.table = "sessions"

    async def create(self) -> Session:
        """Create a new session."""
        result = self.client.table(self.table).insert({}).execute()
        return Session(**result.data[0])

    async def get(self, session_id: str) -> Session | None:
        """Get session by ID."""
        result = (
            self.client.table(self.table)
            .select("*")
            .eq("id", session_id)
            .execute()
        )
        if not result.data:
            return None
        return Session(**result.data[0])

    async def update(self, session_id: str, updates: SessionUpdate) -> Session | None:
        """Update session metadata."""
        update_data = updates.model_dump(exclude_none=True)
        if not update_data:
            return await self.get(session_id)

        result = (
            self.client.table(self.table)
            .update(update_data)
            .eq("id", session_id)
            .execute()
        )
        if not result.data:
            return None
        return Session(**result.data[0])

    async def end(self, session_id: str) -> Session | None:
        """Mark session as ended."""
        result = (
            self.client.table(self.table)
            .update({
                "status": "ended",
                "ended_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", session_id)
            .execute()
        )
        if not result.data:
            return None
        return Session(**result.data[0])

    async def increment_tool_calls(self, session_id: str) -> None:
        """Increment tool calls counter."""
        # Use RPC for atomic increment in production
        session = await self.get(session_id)
        if session:
            await self.update(
                session_id,
                SessionUpdate(tool_calls_count=session.tool_calls_count + 1),
            )

    async def increment_fallbacks(self, session_id: str) -> None:
        """Increment fallback activations counter."""
        session = await self.get(session_id)
        if session:
            await self.update(
                session_id,
                SessionUpdate(fallback_activations=session.fallback_activations + 1),
            )

    async def add_tokens(self, session_id: str, tokens: int) -> None:
        """Add to total tokens count."""
        session = await self.get(session_id)
        if session:
            await self.update(
                session_id,
                SessionUpdate(total_tokens=session.total_tokens + tokens),
            )

    async def list_active(self) -> list[Session]:
        """List all active sessions."""
        result = (
            self.client.table(self.table)
            .select("*")
            .eq("status", "active")
            .order("created_at", desc=True)
            .execute()
        )
        return [Session(**row) for row in result.data]

    async def list_recent(self, limit: int = 50) -> list[Session]:
        """List recent sessions."""
        result = (
            self.client.table(self.table)
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [Session(**row) for row in result.data]


# Singleton instance
session_service = SessionService()
