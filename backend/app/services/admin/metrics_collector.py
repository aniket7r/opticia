"""Metrics collection service.

Collects and stores operational metrics for admin dashboard.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.core.supabase import get_supabase_client

logger = logging.getLogger(__name__)


class MetricType:
    """Metric type constants."""

    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SESSION_DURATION = "session_duration"
    TOKEN_USAGE = "token_usage"
    API_COST = "api_cost"
    TOOL_CALL = "tool_call"
    FALLBACK = "fallback"
    ERROR = "error"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"


class MetricsCollector:
    """Collects operational metrics."""

    def __init__(self) -> None:
        self.client = get_supabase_client()
        self.table = "metrics"

    async def record(
        self,
        metric_type: str,
        value: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a metric."""
        try:
            self.client.table(self.table).insert({
                "metric_type": metric_type,
                "value": value,
                "metadata": metadata or {},
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to record metric: {e}")

    async def record_session_start(self, session_id: str) -> None:
        """Record session start."""
        await self.record(
            MetricType.SESSION_START,
            1,
            {"session_id": session_id},
        )

    async def record_session_end(
        self, session_id: str, duration_seconds: float
    ) -> None:
        """Record session end with duration."""
        await self.record(
            MetricType.SESSION_END,
            1,
            {"session_id": session_id},
        )
        await self.record(
            MetricType.SESSION_DURATION,
            duration_seconds,
            {"session_id": session_id},
        )

    async def record_tokens(
        self, session_id: str, input_tokens: int, output_tokens: int
    ) -> None:
        """Record token usage."""
        await self.record(
            MetricType.TOKEN_USAGE,
            input_tokens + output_tokens,
            {
                "session_id": session_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        )

    async def record_cost(self, session_id: str, cost_usd: float) -> None:
        """Record API cost."""
        await self.record(
            MetricType.API_COST,
            cost_usd,
            {"session_id": session_id},
        )

    async def record_tool_call(self, session_id: str, tool_name: str) -> None:
        """Record tool usage."""
        await self.record(
            MetricType.TOOL_CALL,
            1,
            {"session_id": session_id, "tool_name": tool_name},
        )

    async def record_fallback(
        self, session_id: str, from_mode: str, to_mode: str
    ) -> None:
        """Record fallback event."""
        await self.record(
            MetricType.FALLBACK,
            1,
            {"session_id": session_id, "from": from_mode, "to": to_mode},
        )

    async def record_cache_event(self, hit: bool, tokens: int = 0) -> None:
        """Record cache hit or miss."""
        metric_type = MetricType.CACHE_HIT if hit else MetricType.CACHE_MISS
        await self.record(metric_type, tokens if tokens else 1)

    async def record_error(
        self, session_id: str, error_type: str, message: str
    ) -> None:
        """Record error event."""
        await self.record(
            MetricType.ERROR,
            1,
            {"session_id": session_id, "error_type": error_type, "message": message[:200]},
        )


# Singleton instance
metrics_collector = MetricsCollector()
