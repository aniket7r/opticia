"""Metrics models."""

from datetime import datetime
from typing import Any

from app.models.base import BaseSchema


class MetricCreate(BaseSchema):
    """Request to record a metric."""

    metric_type: str
    value: float
    metadata: dict[str, Any] | None = None


class Metric(BaseSchema):
    """Recorded metric."""

    id: str
    recorded_at: datetime
    metric_type: str
    value: float
    metadata: dict[str, Any] | None = None


class MetricsSummary(BaseSchema):
    """Aggregated metrics summary."""

    total_sessions: int
    active_sessions: int
    total_tokens: int
    total_cost: float
    avg_session_duration_seconds: float | None = None
