"""Health check endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.base import BaseSchema


router = APIRouter(tags=["health"])


class HealthResponse(BaseSchema):
    """Health check response."""

    status: str
    service_name: str
    timestamp: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check service health."""
    return HealthResponse(
        status="healthy",
        service_name="gemini3-backend",
        timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        version="0.1.0",
    )
