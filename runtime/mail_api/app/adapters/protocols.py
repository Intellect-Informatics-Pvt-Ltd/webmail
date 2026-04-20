"""PSense Mail — Adapter protocols.

These define the contracts that every adapter must satisfy.  The adapter
registry selects concrete implementations based on YAML config.  Services
depend only on protocols — never on concrete adapter classes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Protocol, runtime_checkable

from app.domain.models import MailRecipient


# ── Health ───────────────────────────────────────────────────────────────────

@dataclass
class AdapterHealthStatus:
    name: str
    status: Literal["ok", "degraded", "down"]
    latency_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


# ── Transport (outbound mail) ────────────────────────────────────────────────

@dataclass
class OutboundMessage:
    """Normalized outbound message for transport adapters."""
    message_id: str
    from_address: str
    from_name: str
    to: list[MailRecipient]
    cc: list[MailRecipient]
    bcc: list[MailRecipient]
    subject: str
    body_html: str | None = None
    body_text: str | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class TransportReceipt:
    """Result of sending a message via transport adapter."""
    transport_message_id: str | None = None
    accepted_at: datetime | None = None
    diagnostic_code: str | None = None


@runtime_checkable
class TransportAdapter(Protocol):
    """Send outbound mail via a specific provider."""

    async def send(self, message: OutboundMessage) -> TransportReceipt:
        """Send a single message. Raises RetryableDeliveryError or PermanentDeliveryError on failure."""
        ...

    async def health_check(self) -> AdapterHealthStatus:
        ...


# ── Inbound (receive mail) ──────────────────────────────────────────────────

@dataclass
class InboundMessage:
    """Normalized inbound message from a mail provider."""
    provider_message_id: str
    from_address: str
    from_name: str
    to: list[MailRecipient]
    cc: list[MailRecipient]
    subject: str
    body_html: str | None = None
    body_text: str | None = None
    received_at: datetime | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    raw_headers: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class InboundAdapter(Protocol):
    """Receive inbound mail from a provider."""

    async def fetch_new_messages(
        self, mailbox_id: str, since: datetime | None = None,
    ) -> list[InboundMessage]:
        ...

    async def acknowledge(self, message_ids: list[str]) -> None:
        ...

    async def health_check(self) -> AdapterHealthStatus:
        ...


# ── File Storage (NAS / S3 / Azure / GCS) ────────────────────────────────────

@runtime_checkable
class FileStorageAdapter(Protocol):
    """Store and retrieve attachment files."""

    async def store(
        self, path: str, content: bytes, content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Store content at path. Returns the canonical storage path."""
        ...

    async def retrieve(self, path: str) -> tuple[bytes, str]:
        """Retrieve content and its content_type from path."""
        ...

    async def delete(self, path: str) -> None:
        ...

    async def exists(self, path: str) -> bool:
        ...

    async def generate_url(self, path: str, ttl_seconds: int = 3600) -> str:
        """Generate a time-limited access URL. For NAS, returns an API-served path."""
        ...

    async def list_files(self, prefix: str) -> list[str]:
        """List files under a prefix."""
        ...

    async def health_check(self) -> AdapterHealthStatus:
        ...


# ── AV Scanner ──────────────────────────────────────────────────────────────


class AVVerdict(str, Enum):
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"


@dataclass
class AVScanResult:
    verdict: AVVerdict
    threat_name: str | None = None
    scanner_name: str = ""
    scan_duration_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AVScannerAdapter(Protocol):
    """Scan file content for malware / viruses."""

    async def scan(self, content: bytes, filename: str) -> AVScanResult:
        """Scan content. Returns verdict + optional threat name."""
        ...

    async def health_check(self) -> AdapterHealthStatus:
        ...


# ── Search ───────────────────────────────────────────────────────────────────

@runtime_checkable
class SearchAdapter(Protocol):
    """Full-text search indexing and querying."""

    async def index_message(self, user_id: str, message_id: str, content: dict[str, Any]) -> None:
        ...

    async def remove_message(self, user_id: str, message_id: str) -> None:
        ...

    async def search(
        self, user_id: str, query: str,
        filters: dict[str, Any] | None = None,
        cursor: str | None = None, limit: int = 50,
    ) -> dict[str, Any]:
        """Returns {'hits': [MessageDoc...], 'next_cursor': ..., 'total_estimate': int}"""
        ...

    async def suggest(self, user_id: str, partial: str, limit: int = 10) -> list[str]:
        ...

    async def build_facets(
        self, user_id: str, mongo_filter: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        """Build facets (folder distribution, category breakdown) from matching docs."""
        ...

    async def health_check(self) -> AdapterHealthStatus:
        ...


# ── LLM (AI Copilot) ────────────────────────────────────────────────────────


@runtime_checkable
class LLMAdapter(Protocol):
    """Protocol for Large Language Model adapters (AI copilot features)."""

    async def complete(self, prompt: str, max_tokens: int = 512) -> str:
        """Send a prompt and return the completion text."""
        ...

    async def health_check(self) -> AdapterHealthStatus:
        ...

