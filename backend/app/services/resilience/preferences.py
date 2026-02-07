"""User preference persistence.

Stores and retrieves user preferences from Supabase.
"""

import logging
from typing import Any

from pydantic import BaseModel

from app.core.supabase import get_supabase_admin_client

logger = logging.getLogger(__name__)


class UserPreferences(BaseModel):
    """User preferences model."""

    mode: str = "voice"  # voice or text
    proactivity_level: str = "balanced"  # minimal, balanced, proactive
    auto_fallback: bool = True
    show_thinking: bool = True
    camera_position: str = "bottom-right"  # PiP position


DEFAULT_PREFERENCES = UserPreferences()


class PreferencesService:
    """Service for managing user preferences."""

    def __init__(self) -> None:
        self.client = get_supabase_admin_client()
        self.table = "preferences"

    async def get(self, session_id: str) -> UserPreferences:
        """Get preferences for a session, or return defaults."""
        try:
            result = (
                self.client.table(self.table)
                .select("preferences")
                .eq("session_id", session_id)
                .execute()
            )

            if result.data and len(result.data) > 0:
                prefs_data = result.data[0].get("preferences", {})
                return UserPreferences(**prefs_data)

        except Exception as e:
            logger.warning(f"Failed to get preferences: {e}")

        return DEFAULT_PREFERENCES

    async def save(self, session_id: str, preferences: UserPreferences) -> bool:
        """Save preferences for a session."""
        try:
            # Upsert preferences
            self.client.table(self.table).upsert({
                "session_id": session_id,
                "preferences": preferences.model_dump(),
            }).execute()
            return True

        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
            return False

    async def update(
        self, session_id: str, updates: dict[str, Any]
    ) -> UserPreferences:
        """Update specific preferences."""
        current = await self.get(session_id)
        updated_data = current.model_dump()
        updated_data.update(updates)
        updated = UserPreferences(**updated_data)
        await self.save(session_id, updated)
        return updated


# Singleton instance
preferences_service = PreferencesService()
