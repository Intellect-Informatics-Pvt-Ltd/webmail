"""PSense Mail — Authentication middleware.

Supports two modes controlled by `auth.enabled` in settings:

  - **Dev mode** (auth.enabled = false):
    Injects a synthetic user from auth.dev_user_* into request state.
    No JWT validation. Used for local development and testing.

  - **Production mode** (auth.enabled = true):
    Validates Bearer JWT tokens against KeyCloak JWKS endpoint.
    Caches JWKS keys with configurable TTL to avoid hammering KeyCloak.
    Extracts user_id, email, display_name, and roles from claims.
    Returns 401 on missing/invalid/expired tokens.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from config.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class AuthenticatedUser:
    """User identity extracted from JWT or dev config."""
    user_id: str
    email: str
    display_name: str = ""
    roles: list[str] = field(default_factory=list)


# ── JWKS Cache ────────────────────────────────────────────────────────────


class JWKSCache:
    """In-process singleton JWKS cache with configurable TTL.

    Caches the JWKS key set fetched from the KeyCloak JWKS endpoint.
    Uses stale-if-error fallback: serves expired cache on fetch failure.
    """

    def __init__(self, ttl_seconds: int = 300):
        self._ttl = ttl_seconds
        self._cache: dict[str, Any] | None = None
        self._fetched_at: float = 0.0

    @property
    def is_fresh(self) -> bool:
        return self._cache is not None and (time.monotonic() - self._fetched_at) < self._ttl

    @property
    def has_stale(self) -> bool:
        return self._cache is not None

    async def get_jwks(self, jwks_uri: str) -> dict[str, Any]:
        """Get JWKS keys, fetching from URI if cache is expired."""
        if self.is_fresh:
            return self._cache  # type: ignore[return-value]

        import httpx

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(jwks_uri)
                resp.raise_for_status()
                self._cache = resp.json()
                self._fetched_at = time.monotonic()
                return self._cache  # type: ignore[return-value]
        except Exception as exc:
            if self.has_stale:
                logger.warning("JWKS fetch failed, using stale cache: %s", exc)
                return self._cache  # type: ignore[return-value]
            raise  # No cache at all — caller will handle


# Module-level JWKS cache singleton
_jwks_cache: JWKSCache | None = None


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware with dev bypass."""

    # Paths that skip authentication entirely
    SKIP_PATHS = {"/api/v1/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}

    def __init__(self, app, settings: "Settings"):  # noqa: ANN001
        super().__init__(app)
        self._settings = settings
        self._auth_enabled = settings.auth.enabled

        if self._auth_enabled:
            global _jwks_cache
            _jwks_cache = JWKSCache(ttl_seconds=settings.auth.jwks_cache_ttl_seconds)
            logger.info("Auth middleware: KeyCloak JWT validation ENABLED (issuer=%s)", settings.auth.issuer)
        else:
            logger.info(
                "Auth middleware: DEV MODE — all requests authenticated as '%s' (%s)",
                settings.auth.dev_user_id,
                settings.auth.dev_user_email,
            )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth for health/docs endpoints
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        if not self._auth_enabled:
            # Dev mode: inject synthetic user
            request.state.user = AuthenticatedUser(
                user_id=self._settings.auth.dev_user_id,
                email=self._settings.auth.dev_user_email,
                display_name=self._settings.auth.dev_user_name,
                roles=["admin", "member"],
            )
            return await call_next(request)

        # Production mode: validate JWT
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid Authorization header", "code": "UNAUTHENTICATED"},
            )

        token = auth_header.removeprefix("Bearer ").strip()

        try:
            user = await self._validate_token(token)
            request.state.user = user
            return await call_next(request)
        except Exception as e:
            if "JWKS" in str(e) or "fetch" in str(e).lower():
                logger.error("JWKS unavailable: %s", e)
                return JSONResponse(
                    status_code=503,
                    content={"error": "Authentication service unavailable", "code": "AUTH_UNAVAILABLE"},
                )
            logger.warning("JWT validation failed: %s", e)
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or expired token", "code": "UNAUTHENTICATED"},
            )

    async def _validate_token(self, token: str) -> AuthenticatedUser:
        """Validate JWT against KeyCloak JWKS with caching."""
        from jose import jwt as jose_jwt

        global _jwks_cache
        if _jwks_cache is None:
            raise RuntimeError("JWKS cache not initialized")

        jwks = await _jwks_cache.get_jwks(self._settings.auth.jwks_uri)

        payload = jose_jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=self._settings.auth.audience,
            issuer=self._settings.auth.issuer,
        )

        return AuthenticatedUser(
            user_id=payload.get("sub", ""),
            email=payload.get("email", ""),
            display_name=payload.get("name", payload.get("preferred_username", "")),
            roles=payload.get("realm_access", {}).get("roles", []),
        )
