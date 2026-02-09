"""API v1 router aggregating all endpoints."""

from fastapi import APIRouter

from .admin import router as admin_router
from .health import router as health_router
from .metrics import router as metrics_router
from .reports import router as reports_router
from .sessions import router as sessions_router

router = APIRouter(prefix="/api/v1")

router.include_router(health_router)
router.include_router(sessions_router)
router.include_router(metrics_router)
router.include_router(admin_router)
router.include_router(reports_router)
