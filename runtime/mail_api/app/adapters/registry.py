"""PSense Mail — Configuration-driven adapter registry.

Reads settings and instantiates the correct concrete adapter for each
concern (transport, inbound, file_storage, search). Services depend on
protocols — they never know which concrete adapter is active.
"""
from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from app.adapters.protocols import FileStorageAdapter, SearchAdapter, TransportAdapter

if TYPE_CHECKING:
    from config.settings import Settings

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Factory that creates adapters based on settings.

    Usage:
        registry = AdapterRegistry(settings)
        transport = registry.transport   # concrete adapter matching config
    """

    def __init__(self, settings: "Settings"):
        self._settings = settings

    # ── Transport ────────────────────────────────────────────────────────

    @cached_property
    def transport(self) -> TransportAdapter:
        active = self._settings.provider.active
        logger.info("Initialising transport adapter: %s", active)

        if active == "mailpit":
            from app.adapters.transport.mailpit import MailpitTransportAdapter

            cfg = self._settings.provider.mailpit
            return MailpitTransportAdapter(
                smtp_host=cfg.smtp_host,
                smtp_port=cfg.smtp_port,
                from_address=cfg.from_address,
            )
        elif active == "gmail":
            from app.adapters.transport.gmail import GmailTransportAdapter
            return GmailTransportAdapter(
                credentials_file=self._settings.provider.gmail.credentials_file,
                token_file=self._settings.provider.gmail.token_file,
            )
        else:
            from app.adapters.transport.memory import MemoryTransportAdapter

            return MemoryTransportAdapter()

    # ── File Storage ─────────────────────────────────────────────────────

    @cached_property
    def file_storage(self) -> FileStorageAdapter:
        backend = self._settings.file_storage.backend
        logger.info("Initialising file storage adapter: %s", backend)

        if backend == "nas":
            from app.adapters.file_storage.nas import NASStorageAdapter

            cfg = self._settings.file_storage.nas
            return NASStorageAdapter(
                base_path=cfg.base_path,
                max_file_size_mb=cfg.max_file_size_mb,
                allowed_extensions=cfg.allowed_extensions,
            )
        elif backend == "s3":
            from app.adapters.file_storage.s3 import S3StorageAdapter

            cfg = self._settings.file_storage.s3
            return S3StorageAdapter(
                bucket=cfg.bucket,
                region=cfg.region,
                access_key_id=cfg.access_key_id,
                secret_access_key=cfg.secret_access_key,
                endpoint_url=cfg.endpoint_url,
            )
        else:
            raise ValueError(f"Unknown file_storage backend: {backend}")

    # ── Search ───────────────────────────────────────────────────────────

    @cached_property
    def search(self) -> SearchAdapter:
        backend = self._settings.search.backend
        logger.info("Initialising search adapter: %s", backend)

        if backend == "mongo":
            from app.adapters.search.mongo import MongoSearchAdapter

            return MongoSearchAdapter()
        else:
            from app.adapters.search.memory import MemorySearchAdapter

            return MemorySearchAdapter()
