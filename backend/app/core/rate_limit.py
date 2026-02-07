"""Rate limiting middleware for API protection.

Simple in-memory rate limiter for production use.
For distributed deployments, consider Redis-based rate limiting.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10  # Max requests in 1 second


class TokenBucket:
    """Token bucket rate limiter for a single client."""

    def __init__(self, config: RateLimitConfig) -> None:
        self.config = config
        self.tokens = config.burst_limit
        self.last_update = time.time()
        self.minute_count = 0
        self.minute_start = time.time()
        self.hour_count = 0
        self.hour_start = time.time()

    def _refill(self) -> None:
        """Refill tokens based on time passed."""
        now = time.time()
        time_passed = now - self.last_update
        self.tokens = min(
            self.config.burst_limit,
            self.tokens + time_passed * (self.config.requests_per_minute / 60),
        )
        self.last_update = now

        # Reset minute counter
        if now - self.minute_start >= 60:
            self.minute_count = 0
            self.minute_start = now

        # Reset hour counter
        if now - self.hour_start >= 3600:
            self.hour_count = 0
            self.hour_start = now

    def is_allowed(self) -> tuple[bool, str | None]:
        """Check if request is allowed.

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        self._refill()

        # Check hour limit
        if self.hour_count >= self.config.requests_per_hour:
            return False, "hourly_limit_exceeded"

        # Check minute limit
        if self.minute_count >= self.config.requests_per_minute:
            return False, "minute_limit_exceeded"

        # Check burst limit
        if self.tokens < 1:
            return False, "burst_limit_exceeded"

        # Consume token
        self.tokens -= 1
        self.minute_count += 1
        self.hour_count += 1

        return True, None


class RateLimiter:
    """Rate limiter managing multiple clients."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self.buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(self.config)
        )
        self.last_cleanup = time.time()

    def _cleanup_old_buckets(self) -> None:
        """Remove old buckets to prevent memory growth."""
        now = time.time()
        if now - self.last_cleanup < 300:  # Cleanup every 5 minutes
            return

        # Remove buckets not used in last hour
        stale = [
            key
            for key, bucket in self.buckets.items()
            if now - bucket.last_update > 3600
        ]
        for key in stale:
            del self.buckets[key]

        self.last_cleanup = now

    def is_allowed(self, client_id: str) -> tuple[bool, str | None]:
        """Check if client request is allowed."""
        self._cleanup_old_buckets()
        return self.buckets[client_id].is_allowed()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(
        self,
        app,
        limiter: RateLimiter | None = None,
        get_client_id: Callable[[Request], str] | None = None,
        exclude_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.limiter = limiter or RateLimiter()
        self.get_client_id = get_client_id or self._default_client_id
        self.exclude_paths = exclude_paths or ["/health", "/api/v1/health"]

    @staticmethod
    def _default_client_id(request: Request) -> str:
        """Get client ID from request (IP address)."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        """Check rate limit before processing request."""
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # Skip rate limiting for WebSocket upgrades
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        client_id = self.get_client_id(request)
        allowed, reason = self.limiter.is_allowed(client_id)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_id}: {reason}")
            return Response(
                content=f'{{"error": "rate_limit_exceeded", "reason": "{reason}"}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


# Global rate limiter instance
rate_limiter = RateLimiter()
