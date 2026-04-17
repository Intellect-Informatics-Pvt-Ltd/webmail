"""PSense Mail — FastAPI dependencies.

Reusable Depends() callables injected into route handlers.
"""
from __future__ import annotations

from fastapi import Depends, Request

from app.middleware.auth import AuthenticatedUser


async def get_current_user(request: Request) -> AuthenticatedUser:
    """Extract the authenticated user from request state.

    Set by AuthMiddleware — either from JWT claims or dev config.
    """
    user: AuthenticatedUser | None = getattr(request.state, "user", None)
    if user is None:
        from app.domain.errors import AuthenticationError
        raise AuthenticationError("No authenticated user in request state")
    return user


async def get_correlation_id(request: Request) -> str | None:
    """Extract correlation ID from request state."""
    return getattr(request.state, "correlation_id", None)
