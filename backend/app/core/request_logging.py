"""Request logging middleware for observability.

Logs request/response details for production monitoring.
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses."""

    def __init__(
        self,
        app,
        exclude_paths: list[str] | None = None,
        log_body: bool = False,
    ) -> None:
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/api/v1/health"]
        self.log_body = log_body

    async def dispatch(self, request: Request, call_next) -> Response:
        """Log request and response details."""
        # Skip logging for excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # Skip logging for WebSocket upgrades
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]

        # Get client IP
        forwarded = request.headers.get("x-forwarded-for")
        client_ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else (request.client.host if request.client else "unknown")
        )

        # Log request
        start_time = time.time()
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from={client_ip} "
            f"ua={request.headers.get('user-agent', 'unknown')[:50]}"
        )

        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"[{request_id}] {response.status_code} "
                f"duration={duration_ms:.1f}ms"
            )

            # Add request ID header for tracing
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] ERROR {type(e).__name__}: {str(e)[:100]} "
                f"duration={duration_ms:.1f}ms"
            )
            raise
