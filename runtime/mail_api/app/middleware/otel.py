"""PSense Mail — OpenTelemetry instrumentation middleware.

Adds distributed tracing and metrics when OTel is enabled.
Traces every request with span attributes for user_id, correlation_id,
method, path, and status code.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Lazy-loaded tracer and meter — only initialized when OTel is enabled
_tracer = None
_meter = None
_request_counter = None
_request_duration = None


def _init_otel(endpoint: str) -> None:
    """Initialize OpenTelemetry SDK (tracer + meter) lazily."""
    global _tracer, _meter, _request_counter, _request_duration

    try:
        from opentelemetry import trace, metrics
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanExporter
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": "psense-mail-api"})

        # Tracer
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanExporter(OTLPSpanExporter(endpoint=endpoint))
        )
        trace.set_tracer_provider(tracer_provider)
        _tracer = trace.get_tracer("psense.mail")

        # Meter
        meter_provider = MeterProvider(resource=resource)
        metrics.set_meter_provider(meter_provider)
        _meter = metrics.get_meter("psense.mail")
        _request_counter = _meter.create_counter(
            "http.server.request.count",
            description="Total HTTP requests",
        )
        _request_duration = _meter.create_histogram(
            "http.server.request.duration",
            description="HTTP request duration in milliseconds",
            unit="ms",
        )

        logger.info("OpenTelemetry initialized (endpoint=%s)", endpoint)

    except ImportError:
        logger.warning("OpenTelemetry packages not installed — tracing disabled")
    except Exception as exc:
        logger.warning("OpenTelemetry initialization failed: %s", exc)


class OpenTelemetryMiddleware(BaseHTTPMiddleware):
    """Adds OpenTelemetry tracing and metrics to each request."""

    def __init__(self, app: Any, otel_endpoint: str = "http://localhost:4317"):
        super().__init__(app)
        _init_otel(otel_endpoint)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not _tracer:
            return await call_next(request)

        method = request.method
        path = request.url.path
        correlation_id = request.headers.get("X-Correlation-ID", "")
        user_id = getattr(request.state, "user_id", "") if hasattr(request, "state") else ""

        with _tracer.start_as_current_span(
            f"{method} {path}",
            attributes={
                "http.method": method,
                "http.url": str(request.url),
                "http.route": path,
                "psense.correlation_id": correlation_id,
                "psense.user_id": user_id,
            },
        ) as span:
            start = time.monotonic()
            response = await call_next(request)
            duration_ms = (time.monotonic() - start) * 1000

            span.set_attribute("http.status_code", response.status_code)

            # Record metrics
            labels = {"method": method, "path": path, "status": str(response.status_code)}
            if _request_counter:
                _request_counter.add(1, labels)
            if _request_duration:
                _request_duration.record(duration_ms, labels)

            return response
