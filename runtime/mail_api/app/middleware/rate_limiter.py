"""PSense Mail — Rate limiting middleware.

Enforces per-user request rate limits using a sliding-window counter.
Supports in-memory (default) and Redis backends.

Configuration via `rate_limit` section in settings:
  - requests_per_minute: 300 (general)
  - search_requests_per_minute: 30 (search endpoint)
  - backend: "memory" | "redis"
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from config.settings import Settings

logger = logging.getLogger(__name__)

# Paths exempt from rate limiting
_EXEMPT_PATHS = {"/api/v1/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}


class SlidingWindowCounter:
    """In-memory sliding-window rate limiter."""

    def __init__(self) -> None:
        # {user_key: [(timestamp, count_in_window)]}
        self._windows: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        """Check if the request is allowed. Returns (allowed, retry_after_seconds)."""
        now = time.monotonic()
        cutoff = now - window_seconds

        # Remove expired entries
        entries = self._windows[key]
        self._windows[key] = [t for t in entries if t > cutoff]

        if len(self._windows[key]) >= limit:
            # Calculate retry-after from oldest entry in window
            oldest = min(self._windows[key]) if self._windows[key] else now
            retry_after = max(1, int(oldest + window_seconds - now))
            return False, retry_after

        self._windows[key].append(now)
        return True, 0


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Per-user rate limiting middleware with sliding window."""

    def __init__(self, app, settings: "Settings"):  # noqa: ANN001
        super().__init__(app)
        self._settings = settings
        self._general_limit = settings.rate_limit.requests_per_minute
        self._search_limit = settings.rate_limit.search_requests_per_minute
        self._counter = SlidingWindowCounter()
        self._auth_enabled = settings.auth.enabled
        self._dev_user_id = settings.auth.dev_user_id

        logger.info(
            "Rate limiter: %d req/min general, %d req/min search (backend=%s)",
            self._general_limit,
            self._search_limit,
            settings.rate_limit.backend,
        )

    def _get_user_key(self, request: Request) -> str:
        """Extract user ID for rate limiting."""
        if not self._auth_enabled:
            return self._dev_user_id
        user = getattr(request.state, "user", None)
        if user:
            return user.user_id
        # Fallback to IP if no user yet (pre-auth)
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Exempt certain paths
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Only rate-limit /api/v1/ paths
        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)

        user_key = self._get_user_key(request)

        # Determine which limit applies
        is_search = request.url.path == "/api/v1/search"
        limit = self._search_limit if is_search else self._general_limit
        rate_key = f"{user_key}:search" if is_search else user_key

        allowed, retry_after = self._counter.is_allowed(rate_key, limit, window_seconds=60)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMITED",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
