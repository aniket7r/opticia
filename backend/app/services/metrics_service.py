"""Metrics tracking service."""

from typing import Any

from app.core.supabase import get_supabase_client
from app.models.metrics import Metric, MetricsSummary


class MetricsService:
    """Service for tracking and aggregating metrics."""

    def __init__(self) -> None:
        self.client = get_supabase_client()
        self.metrics_table = "metrics"
        self.sessions_table = "sessions"

    async def record(
        self,
        metric_type: str,
        value: float,
        metadata: dict[str, Any] | None = None,
    ) -> Metric:
        """Record a metric."""
        result = (
            self.client.table(self.metrics_table)
            .insert({
                "metric_type": metric_type,
                "value": value,
                "metadata": metadata or {},
            })
            .execute()
        )
        return Metric(**result.data[0])

    async def record_cost(self, session_id: str, cost: float) -> Metric:
        """Record session cost."""
        return await self.record(
            metric_type="session_cost",
            value=cost,
            metadata={"session_id": session_id},
        )

    async def record_tokens(self, session_id: str, tokens: int) -> Metric:
        """Record token usage."""
        return await self.record(
            metric_type="token_usage",
            value=float(tokens),
            metadata={"session_id": session_id},
        )

    async def record_latency(self, session_id: str, latency_ms: float) -> Metric:
        """Record response latency."""
        return await self.record(
            metric_type="response_latency",
            value=latency_ms,
            metadata={"session_id": session_id},
        )

    async def get_summary(self) -> MetricsSummary:
        """Get aggregated metrics summary."""
        # Get session counts
        all_sessions = (
            self.client.table(self.sessions_table)
            .select("id, status, total_tokens, created_at, ended_at")
            .execute()
        )

        total_sessions = len(all_sessions.data)
        active_sessions = sum(1 for s in all_sessions.data if s["status"] == "active")
        total_tokens = sum(s["total_tokens"] or 0 for s in all_sessions.data)

        # Calculate average session duration
        durations = []
        for s in all_sessions.data:
            if s["ended_at"] and s["created_at"]:
                from datetime import datetime
                created = datetime.fromisoformat(s["created_at"].replace("Z", "+00:00"))
                ended = datetime.fromisoformat(s["ended_at"].replace("Z", "+00:00"))
                durations.append((ended - created).total_seconds())

        avg_duration = sum(durations) / len(durations) if durations else None

        # Get total cost from metrics
        cost_metrics = (
            self.client.table(self.metrics_table)
            .select("value")
            .eq("metric_type", "session_cost")
            .execute()
        )
        total_cost = sum(m["value"] for m in cost_metrics.data)

        return MetricsSummary(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_tokens=total_tokens,
            total_cost=total_cost,
            avg_session_duration_seconds=avg_duration,
        )

    async def get_recent(
        self,
        metric_type: str | None = None,
        limit: int = 100,
    ) -> list[Metric]:
        """Get recent metrics, optionally filtered by type."""
        query = self.client.table(self.metrics_table).select("*")

        if metric_type:
            query = query.eq("metric_type", metric_type)

        result = query.order("recorded_at", desc=True).limit(limit).execute()
        return [Metric(**row) for row in result.data]


# Singleton instance
metrics_service = MetricsService()
