"""PSense Mail — In-memory transport adapter.

Used for unit tests and dev mode when no real mail server is needed.
Stores sent messages in memory for assertion.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.adapters.protocols import AdapterHealthStatus, OutboundMessage, TransportReceipt

logger = logging.getLogger(__name__)


class MemoryTransportAdapter:
    """In-memory transport — stores messages for testing, never sends real mail."""

    def __init__(self) -> None:
        self.sent_messages: list[OutboundMessage] = []
        logger.info("In-memory transport adapter initialised")

    async def send(self, message: OutboundMessage) -> TransportReceipt:
        self.sent_messages.append(message)
        logger.info("In-memory transport: captured message %s to %s", message.message_id, message.to)
        return TransportReceipt(
            transport_message_id=f"mem-{message.message_id}",
            accepted_at=datetime.now(timezone.utc),
        )

    async def health_check(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(name="memory-transport", status="ok")
