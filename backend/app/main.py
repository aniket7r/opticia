"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.services.tools.init_tools import get_tool_count, init_all_tools
from app.ws.router import router as ws_router

import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    setup_logging(debug=settings.debug)
    init_all_tools()
    logger.info(f"Initialized {get_tool_count()} tools")
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    description="AI that sees and guides - real-time visual understanding with voice guidance",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"service": "opticia-ai-backend", "status": "running"}
