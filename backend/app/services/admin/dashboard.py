"""Admin dashboard data service.

Provides aggregated metrics for the admin dashboard.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel

from app.core.supabase import get_supabase_admin_client
from app.ws.connection import manager

logger = logging.getLogger(__name__)


class DashboardStats(BaseModel):
    """Aggregated dashboard statistics."""

    active_sessions: int = 0
    total_sessions_today: int = 0
    total_tokens_today: int = 0
    total_cost_today: float = 0.0
    cache_hit_rate: float = 0.0
    avg_session_duration: float = 0.0
    fallback_count_today: int = 0
    error_count_today: int = 0
    tool_usage: dict[str, int] = {}


class DashboardService:
    """Provides data for admin dashboard."""

    def __init__(self) -> None:
        self.client = get_supabase_admin_client()

    def get_active_sessions(self) -> int:
        """Get current active WebSocket connections."""
        return manager.active_count

    async def get_stats(self) -> DashboardStats:
        """Get aggregated dashboard statistics."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        stats = DashboardStats(active_sessions=self.get_active_sessions())

        try:
            # Get today's metrics
            result = (
                self.client.table("metrics")
                .select("metric_type, value, metadata")
                .gte("recorded_at", today_start)
                .execute()
            )

            if not result.data:
                return stats

            # Aggregate metrics
            sessions = set()
            total_tokens = 0
            total_cost = 0.0
            cache_hits = 0
            cache_misses = 0
            durations = []
            fallbacks = 0
            errors = 0
            tool_usage: dict[str, int] = {}

            for row in result.data:
                metric_type = row["metric_type"]
                value = row["value"]
                metadata = row.get("metadata", {})

                if metric_type == "session_start":
                    sessions.add(metadata.get("session_id"))
                elif metric_type == "token_usage":
                    total_tokens += int(value)
                elif metric_type == "api_cost":
                    total_cost += float(value)
                elif metric_type == "cache_hit":
                    cache_hits += int(value)
                elif metric_type == "cache_miss":
                    cache_misses += int(value)
                elif metric_type == "session_duration":
                    durations.append(float(value))
                elif metric_type == "fallback":
                    fallbacks += 1
                elif metric_type == "error":
                    errors += 1
                elif metric_type == "tool_call":
                    tool_name = metadata.get("tool_name", "unknown")
                    tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

            stats.total_sessions_today = len(sessions)
            stats.total_tokens_today = total_tokens
            stats.total_cost_today = round(total_cost, 4)
            stats.fallback_count_today = fallbacks
            stats.error_count_today = errors
            stats.tool_usage = tool_usage

            # Calculate cache hit rate
            total_cache = cache_hits + cache_misses
            if total_cache > 0:
                stats.cache_hit_rate = round(cache_hits / total_cache * 100, 1)

            # Calculate average session duration
            if durations:
                stats.avg_session_duration = round(sum(durations) / len(durations), 1)

        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")

        return stats

    async def get_recent_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent session metadata."""
        try:
            result = (
                self.client.table("sessions")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get recent sessions: {e}")
            return []

    async def get_cost_by_day(self, days: int = 7) -> list[dict[str, Any]]:
        """Get daily cost breakdown."""
        start_date = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).isoformat()

        try:
            result = (
                self.client.table("metrics")
                .select("recorded_at, value")
                .eq("metric_type", "api_cost")
                .gte("recorded_at", start_date)
                .execute()
            )

            # Group by day
            daily_costs: dict[str, float] = {}
            for row in result.data or []:
                day = row["recorded_at"][:10]
                daily_costs[day] = daily_costs.get(day, 0) + float(row["value"])

            return [
                {"date": day, "cost": round(cost, 4)}
                for day, cost in sorted(daily_costs.items())
            ]
        except Exception as e:
            logger.error(f"Failed to get cost by day: {e}")
            return []


# Singleton instance
dashboard_service = DashboardService()
