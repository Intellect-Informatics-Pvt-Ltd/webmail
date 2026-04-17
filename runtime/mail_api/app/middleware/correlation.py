"""PSense Mail — Correlation ID middleware.

Injects a unique correlation ID into every request/response for
distributed tracing and log correlation.
"""
from __future__ import annotations

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Attach X-Correlation-ID to every request and response."""

    def __init__(self, app, header_name: str = "X-Correlation-ID"):  # noqa: ANN001
        super().__init__(app)
        self._header = header_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Use client-provided correlation ID or generate a new one
        correlation_id = request.headers.get(self._header) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers[self._header] = correlation_id
        return response
