"""Admin API endpoints.

Provides dashboard data and operational metrics for admin interface.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.admin.dashboard import dashboard_service, DashboardStats
from app.services.admin.metrics_collector import metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats() -> DashboardStats:
    """Get aggregated dashboard statistics.

    Returns current operational metrics including:
    - Active WebSocket connections
    - Today's session count, token usage, and costs
    - Cache hit rate
    - Fallback and error counts
    - Tool usage breakdown
    """
    return await dashboard_service.get_stats()


@router.get("/sessions")
async def get_recent_sessions(
    limit: int = Query(default=20, ge=1, le=100)
) -> list[dict[str, Any]]:
    """Get recent session metadata.

    Args:
        limit: Maximum number of sessions to return (1-100)

    Returns:
        List of recent sessions with metadata
    """
    return await dashboard_service.get_recent_sessions(limit)


@router.get("/costs")
async def get_cost_breakdown(
    days: int = Query(default=7, ge=1, le=30)
) -> list[dict[str, Any]]:
    """Get daily cost breakdown.

    Args:
        days: Number of days to include (1-30)

    Returns:
        List of daily costs with date and amount
    """
    return await dashboard_service.get_cost_by_day(days)


@router.get("/health")
async def admin_health_check() -> dict[str, Any]:
    """Admin health check with extended diagnostics."""
    from app.ws.connection import manager

    return {
        "status": "healthy",
        "active_connections": manager.active_count,
        "service": "opticia-admin",
    }
