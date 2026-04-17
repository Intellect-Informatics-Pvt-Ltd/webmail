"""PSense Mail — Gmail transport adapter.

TODO(Phase 6): Implement Gmail API outbound transport provider.
"""
from __future__ import annotations

from app.adapters.protocols import AdapterHealthStatus, OutboundMessage, TransportAdapter, TransportReceipt


class GmailTransportAdapter(TransportAdapter):
    """Send outbound mail via Google Workspace / Gmail API."""

    def __init__(self, credentials_file: str, token_file: str):
        self._credentials_file = credentials_file
        self._token_file = token_file

    async def send(self, message: OutboundMessage) -> TransportReceipt:
        # TODO(Phase 6): Use google-api-python-client or aiohttp to call Gmail API
        # encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        # await gmail_service.users().messages().send(userId='me', body={'raw': encoded_message}).execute()
        raise NotImplementedError("Gmail transport adapter is planned for Phase 6")

    async def health_check(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(
            name="gmail-transport",
            status="degraded",
            details={"error": "Not implemented yet"},
        )
