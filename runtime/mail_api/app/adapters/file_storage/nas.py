"""PSense Mail — NAS (local filesystem / network-attached storage) adapter.

Primary file storage adapter. Stores attachments under a configurable base
path using the convention:

    {base_path}/{user_id}/{message_id}/{attachment_id}-{filename}

For dev, base_path defaults to ./data/attachments.
For production, mount a NAS volume (NFS, SMB, etc.) at the configured path.
"""
from __future__ import annotations

import logging
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

from app.adapters.protocols import AdapterHealthStatus, FileStorageAdapter

logger = logging.getLogger(__name__)


class NASStorageAdapter:
    """Local filesystem / NAS file storage adapter.

    Implements the FileStorageAdapter protocol using aiofiles for async I/O.
    """

    def __init__(self, base_path: str, max_file_size_mb: int = 25, allowed_extensions: list[str] | None = None):
        self._base_path = Path(base_path).resolve()
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self._allowed_extensions = allowed_extensions or ["*"]

        # Ensure base directory exists
        self._base_path.mkdir(parents=True, exist_ok=True)
        logger.info("NAS storage initialised at %s (max %dMB)", self._base_path, max_file_size_mb)

    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative storage path to an absolute filesystem path.

        Prevents path traversal attacks by ensuring the resolved path is
        within the base directory.
        """
        resolved = (self._base_path / path).resolve()
        if not str(resolved).startswith(str(self._base_path)):
            raise ValueError(f"Path traversal detected: {path}")
        return resolved

    async def store(
        self, path: str, content: bytes, content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Store content at the given path under base_path."""
        if len(content) > self._max_file_size_bytes:
            raise ValueError(
                f"File size {len(content)} exceeds maximum {self._max_file_size_bytes} bytes"
            )

        full_path = self._resolve_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)

        logger.debug("Stored %d bytes at %s", len(content), path)
        return path

    async def retrieve(self, path: str) -> tuple[bytes, str]:
        """Retrieve file content and its MIME type."""
        full_path = self._resolve_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(full_path, "rb") as f:
            content = await f.read()

        content_type = mimetypes.guess_type(str(full_path))[0] or "application/octet-stream"
        return content, content_type

    async def delete(self, path: str) -> None:
        """Delete a file."""
        full_path = self._resolve_path(path)
        if full_path.exists():
            await aiofiles.os.remove(full_path)
            logger.debug("Deleted %s", path)

            # Clean up empty parent directories
            parent = full_path.parent
            while parent != self._base_path:
                try:
                    if not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break
                except OSError:
                    break

    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        full_path = self._resolve_path(path)
        return full_path.exists()

    async def generate_url(self, path: str, ttl_seconds: int = 3600) -> str:
        """Generate an API-served download URL.

        For NAS storage, files are served via the API's attachment download
        endpoint, not via direct filesystem access. The URL format is:
            /api/v1/attachments/download?path={path}

        The ttl_seconds parameter is accepted for protocol compatibility
        but not enforced for NAS (auth middleware handles access control).
        """
        # URL-safe path — the API router will resolve and serve the file
        return f"/api/v1/attachments/download?path={path}"

    async def list_files(self, prefix: str) -> list[str]:
        """List all files under a prefix directory."""
        full_path = self._resolve_path(prefix)
        if not full_path.exists() or not full_path.is_dir():
            return []

        result: list[str] = []
        for root, _dirs, files in os.walk(full_path):
            for fname in files:
                abs_path = Path(root) / fname
                rel_path = abs_path.relative_to(self._base_path)
                result.append(str(rel_path))

        return result

    async def health_check(self) -> AdapterHealthStatus:
        """Check filesystem accessibility."""
        start = time.monotonic()
        try:
            # Write + read a canary file
            canary = self._base_path / ".health_check"
            async with aiofiles.open(canary, "w") as f:
                await f.write("ok")
            await aiofiles.os.remove(canary)

            latency = (time.monotonic() - start) * 1000
            return AdapterHealthStatus(name="nas", status="ok", latency_ms=round(latency, 2))
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return AdapterHealthStatus(
                name="nas", status="down", latency_ms=round(latency, 2),
                details={"error": str(e)},
            )
