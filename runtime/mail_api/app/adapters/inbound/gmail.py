"""PSense Mail — Gmail inbound adapter.

TODO(Phase 6): Implement Gmail API inbound push/poll provider.
"""
from __future__ import annotations

from datetime import datetime

from app.adapters.protocols import AdapterHealthStatus, InboundAdapter, InboundMessage


class GmailInboundAdapter(InboundAdapter):
    """Receive inbound mail from Google Workspace / Gmail API."""

    def __init__(self, credentials_file: str, token_file: str, watch_topic: str):
        self._credentials_file = credentials_file
        self._token_file = token_file
        self._watch_topic = watch_topic

    async def fetch_new_messages(
        self, mailbox_id: str, since: datetime | None = None,
    ) -> list[InboundMessage]:
        # TODO(Phase 6): Fetch messages matching `is:unread` or based on historyId from PubSub push
        raise NotImplementedError("Gmail inbound adapter is planned for Phase 6")

    async def acknowledge(self, message_ids: list[str]) -> None:
        # TODO(Phase 6): Remove UNREAD label from messages
        raise NotImplementedError("Gmail inbound adapter is planned for Phase 6")

    async def health_check(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(
            name="gmail-inbound",
            status="degraded",
            details={"error": "Not implemented yet"},
        )
