"""PSense Mail — Memory inbound adapter (test stub).

A simple InboundAdapter implementation that returns a configurable list of
messages. Useful for unit tests and the default 'memory' provider mode where
no live mail server is required.
"""
from __future__ import annotations

from datetime import datetime

from app.adapters.protocols import AdapterHealthStatus, InboundAdapter, InboundMessage


class MemoryInboundAdapter(InboundAdapter):
    """Test double that satisfies the InboundAdapter protocol.

    Messages can be injected at construction time or via `inject_messages()`.
    """

    def __init__(self, messages: list[InboundMessage] | None = None) -> None:
        self._messages: list[InboundMessage] = list(messages) if messages else []

    def inject_messages(self, messages: list[InboundMessage]) -> None:
        """Add messages to the internal queue (for test setup)."""
        self._messages.extend(messages)

    async def fetch_new_messages(
        self, mailbox_id: str, since: datetime | None = None,
    ) -> list[InboundMessage]:
        """Return all injected messages, then clear the internal queue."""
        if since:
            result = [m for m in self._messages if m.received_at and m.received_at >= since]
        else:
            result = list(self._messages)
        # Clear after fetch (simulates one-time delivery)
        self._messages = [m for m in self._messages if m not in result]
        return result

    async def acknowledge(self, message_ids: list[str]) -> None:
        """Remove acknowledged messages from internal list."""
        id_set = set(message_ids)
        self._messages = [m for m in self._messages if m.provider_message_id not in id_set]

    async def health_check(self) -> AdapterHealthStatus:
        """Always healthy."""
        return AdapterHealthStatus(
            name="memory-inbound",
            status="ok",
            latency_ms=0.0,
        )
