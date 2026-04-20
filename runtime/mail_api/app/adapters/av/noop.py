"""PSense Mail — No-op AV scanner adapter.

Always returns CLEAN. Used in development and when AV scanning is disabled.
"""
from __future__ import annotations

from app.adapters.protocols import (
    AVScanResult,
    AVVerdict,
    AdapterHealthStatus,
    AVScannerAdapter,
)


class NoOpAVScanner:
    """AV scanner that always reports files as clean."""

    async def scan(self, content: bytes, filename: str) -> AVScanResult:
        return AVScanResult(
            verdict=AVVerdict.CLEAN,
            scanner_name="noop",
            scan_duration_ms=0.0,
        )

    async def health_check(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(name="av_scanner_noop", status="ok", latency_ms=0.0)
