"""Metrics API endpoints."""

from fastapi import APIRouter

from app.models.metrics import Metric, MetricsSummary
from app.services.metrics_service import metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary() -> MetricsSummary:
    """Get aggregated metrics summary."""
    return await metrics_service.get_summary()


@router.get("", response_model=list[Metric])
async def list_metrics(
    metric_type: str | None = None,
    limit: int = 100,
) -> list[Metric]:
    """List recent metrics."""
    return await metrics_service.get_recent(metric_type=metric_type, limit=limit)
