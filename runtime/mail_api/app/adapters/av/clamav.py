"""PSense Mail — ClamAV scanner adapter.

Connects to a ClamAV daemon (clamd) over TCP and scans file content
using the INSTREAM command. Falls back to ERROR verdict on connection
failures so callers can quarantine or retry.
"""
from __future__ import annotations

import asyncio
import logging
import struct
import time
from typing import Any

from app.adapters.protocols import (
    AVScanResult,
    AVVerdict,
    AdapterHealthStatus,
)

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 8192  # ClamAV INSTREAM chunk size


class ClamAVScanner:
    """AV scanner using ClamAV daemon (clamd) over TCP."""

    def __init__(self, host: str = "localhost", port: int = 3310, timeout: float = 30.0):
        self._host = host
        self._port = port
        self._timeout = timeout

    async def scan(self, content: bytes, filename: str) -> AVScanResult:
        """Send content to ClamAV via INSTREAM protocol and return verdict."""
        start = time.monotonic()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout,
            )

            # Send INSTREAM command
            writer.write(b"zINSTREAM\0")

            # Send content in chunks with 4-byte big-endian length prefix
            offset = 0
            while offset < len(content):
                chunk = content[offset : offset + _CHUNK_SIZE]
                writer.write(struct.pack(">I", len(chunk)) + chunk)
                offset += len(chunk)

            # End of stream — zero-length chunk
            writer.write(struct.pack(">I", 0))
            await writer.drain()

            # Read response
            response = await asyncio.wait_for(reader.read(4096), timeout=self._timeout)
            writer.close()
            await writer.wait_closed()

            elapsed_ms = (time.monotonic() - start) * 1000
            response_text = response.decode("utf-8", errors="replace").strip()

            if "OK" in response_text and "FOUND" not in response_text:
                return AVScanResult(
                    verdict=AVVerdict.CLEAN,
                    scanner_name="clamav",
                    scan_duration_ms=elapsed_ms,
                )
            elif "FOUND" in response_text:
                # Response format: "stream: <threat_name> FOUND"
                threat = response_text.replace("stream:", "").replace("FOUND", "").strip()
                return AVScanResult(
                    verdict=AVVerdict.INFECTED,
                    threat_name=threat or "unknown",
                    scanner_name="clamav",
                    scan_duration_ms=elapsed_ms,
                )
            else:
                return AVScanResult(
                    verdict=AVVerdict.ERROR,
                    scanner_name="clamav",
                    scan_duration_ms=elapsed_ms,
                    details={"raw_response": response_text},
                )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.error("ClamAV scan failed for %s: %s", filename, exc)
            return AVScanResult(
                verdict=AVVerdict.ERROR,
                scanner_name="clamav",
                scan_duration_ms=elapsed_ms,
                details={"error": str(exc)},
            )

    async def health_check(self) -> AdapterHealthStatus:
        """Send PING to clamd and expect PONG."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=5.0,
            )
            start = time.monotonic()
            writer.write(b"zPING\0")
            await writer.drain()
            response = await asyncio.wait_for(reader.read(64), timeout=5.0)
            writer.close()
            await writer.wait_closed()
            latency = (time.monotonic() - start) * 1000

            if b"PONG" in response:
                return AdapterHealthStatus(name="av_scanner_clamav", status="ok", latency_ms=latency)
            return AdapterHealthStatus(
                name="av_scanner_clamav", status="degraded", latency_ms=latency,
                details={"response": response.decode(errors="replace")},
            )
        except Exception as exc:
            return AdapterHealthStatus(
                name="av_scanner_clamav", status="down",
                details={"error": str(exc)},
            )
