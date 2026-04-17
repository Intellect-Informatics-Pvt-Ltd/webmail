"""PSense Mail — FastAPI dependencies.

Reusable Depends() callables injected into route handlers.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, Request

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


async def get_account_id(
    x_account_id: str | None = Header(default=None, alias="X-Account-Id"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> str:
    """Resolve the active account ID.

    Clients pass X-Account-Id when operating on a non-primary account
    (multi-account, delegation). Defaults to user_id for single-account
    scenarios (backward compatible with dev/test seed).
    """
    return x_account_id or user.user_id


async def get_tenant_id(
    user: AuthenticatedUser = Depends(get_current_user),
) -> str:
    """Resolve the active tenant ID.

    In production, extracted from JWT 'tenant_id' claim.
    In dev mode (auth disabled), returns 'default'.
    """
    return getattr(user, "tenant_id", "default") or "default"


@dataclass
class RequestContext:
    """Bundled request context passed to services."""
    user_id: str
    tenant_id: str
    account_id: str
    correlation_id: str | None = None


async def get_request_context(
    user: AuthenticatedUser = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    account_id: str = Depends(get_account_id),
    correlation_id: str | None = Depends(get_correlation_id),
) -> RequestContext:
    """Convenience dependency that bundles all request-scoped context."""
    return RequestContext(
        user_id=user.user_id,
        tenant_id=tenant_id,
        account_id=account_id,
        correlation_id=correlation_id,
    )
