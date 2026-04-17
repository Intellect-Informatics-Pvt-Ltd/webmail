"""PSense Mail — Domain exception → HTTP response mapper.

Catches domain exceptions thrown by services and converts them into
structured JSON error responses with appropriate HTTP status codes.
"""
from __future__ import annotations

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.domain.errors import (
    AuthenticationError,
    AuthorizationError,
    ConcurrencyError,
    ConflictError,
    MailDomainError,
    NotFoundError,
    PermanentDeliveryError,
    PolicyDeniedError,
    ProviderUnavailableError,
    RateLimitedError,
    RetryableDeliveryError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Map domain exception types to HTTP status codes
_STATUS_MAP: dict[type[MailDomainError], int] = {
    NotFoundError: 404,
    ValidationError: 422,
    ConflictError: 409,
    ConcurrencyError: 409,
    PolicyDeniedError: 403,
    AuthenticationError: 401,
    AuthorizationError: 403,
    ProviderUnavailableError: 502,
    RateLimitedError: 429,
    RetryableDeliveryError: 502,
    PermanentDeliveryError: 502,
}


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global exception handler that maps domain errors to HTTP responses."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except MailDomainError as exc:
            status = _STATUS_MAP.get(type(exc), 500)
            correlation_id = getattr(request.state, "correlation_id", None)

            if status >= 500:
                logger.error("Domain error [%s]: %s", exc.code, exc, exc_info=True)
            else:
                logger.warning("Domain error [%s]: %s", exc.code, exc)

            return JSONResponse(
                status_code=status,
                content={
                    "error": str(exc),
                    "code": exc.code,
                    "details": exc.details,
                    "correlation_id": correlation_id,
                },
            )
        except Exception as exc:
            correlation_id = getattr(request.state, "correlation_id", None)
            logger.exception("Unhandled exception: %s", exc)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "code": "INTERNAL_ERROR",
                    "details": {},
                    "correlation_id": correlation_id,
                },
            )
