"""PSense Mail — Configuration-driven adapter registry.

Reads settings and instantiates the correct concrete adapter for each
concern (transport, inbound, file_storage, search). Services depend on
protocols — they never know which concrete adapter is active.
"""
from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from app.adapters.protocols import AVScannerAdapter, FileStorageAdapter, InboundAdapter, LLMAdapter, SearchAdapter, TransportAdapter

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

    # ── Inbound ──────────────────────────────────────────────────────────

    @cached_property
    def inbound(self) -> InboundAdapter:
        active = self._settings.provider.active
        logger.info("Initialising inbound adapter: %s", active)

        if active == "pop3":
            from app.adapters.inbound.pop3 import POP3InboundAdapter
            from app.adapters.inbound.seen_store import create_seen_store

            cfg = self._settings.provider.pop3
            if not cfg.username:
                raise ValueError(
                    "provider.pop3.username is required when provider.active is 'pop3'"
                )
            store = create_seen_store(self._settings.database.backend)
            return POP3InboundAdapter(config=cfg, seen_store=store)
        elif active == "mailpit":
            from app.adapters.inbound.mailpit import MailPitInboundAdapter

            return MailPitInboundAdapter(api_url=self._settings.provider.mailpit.api_url)
        elif active == "gmail":
            from app.adapters.inbound.gmail import GmailInboundAdapter

            cfg = self._settings.provider.gmail
            return GmailInboundAdapter(
                credentials_file=cfg.credentials_file,
                token_file=cfg.token_file,
                watch_topic=cfg.watch_topic,
            )
        elif active == "imap":
            from app.adapters.inbound.imap import IMAPInboundAdapter

            cfg = self._settings.provider.imap
            return IMAPInboundAdapter(
                host=cfg.host, port=cfg.port,
                username=cfg.username, password=cfg.password,
                tls_mode=cfg.tls_mode, mailbox=cfg.mailbox,
                connect_timeout=cfg.connect_timeout_seconds,
            )
        elif active == "msgraph":
            from app.adapters.inbound.msgraph import MicrosoftGraphInboundAdapter

            cfg = self._settings.provider.msgraph
            return MicrosoftGraphInboundAdapter(
                tenant_id=cfg.tenant_id,
                client_id=cfg.client_id,
                client_secret=cfg.client_secret,
                redirect_uri=cfg.redirect_uri,
                scopes=cfg.scopes,
            )
        else:
            from app.adapters.inbound.memory import MemoryInboundAdapter

            return MemoryInboundAdapter()

    # ── AV Scanner ────────────────────────────────────────────────────────────

    @cached_property
    def av_scanner(self) -> AVScannerAdapter:
        active = self._settings.provider.active
        logger.info("Initialising AV scanner adapter")

        # For now, use NoOp in dev / memory mode, ClamAV when configured
        # Can be extended with a dedicated av.backend setting later
        try:
            from app.adapters.av.clamav import ClamAVScanner
            return ClamAVScanner()
        except Exception:
            from app.adapters.av.noop import NoOpAVScanner
            return NoOpAVScanner()

    # ── LLM (AI Copilot) ────────────────────────────────────────────────

    @cached_property
    def llm(self) -> LLMAdapter:
        backend = self._settings.copilot.llm_backend
        logger.info("Initialising LLM adapter: %s", backend)

        if backend == "openai":
            from app.adapters.llm.openai_adapter import OpenAILLMAdapter
            return OpenAILLMAdapter(
                api_key=self._settings.copilot.openai_api_key,
                model=self._settings.copilot.openai_model,
                base_url=self._settings.copilot.openai_base_url or None,
            )
        elif backend == "ollama":
            from app.adapters.llm.openai_adapter import OpenAILLMAdapter
            # Ollama exposes an OpenAI-compatible API at /v1
            base = self._settings.copilot.ollama_base_url.rstrip("/")
            return OpenAILLMAdapter(
                api_key="ollama",  # Ollama doesn't require a real key
                model=self._settings.copilot.ollama_model,
                base_url=f"{base}/v1",
            )
        else:
            from app.adapters.llm.noop import NoOpLLMAdapter
            return NoOpLLMAdapter()

