"""PSense Mail — MailPit inbound adapter.

Polls the MailPit REST API for new incoming messages.
"""
from __future__ import annotations

import logging
from datetime import datetime
import httpx

from app.adapters.protocols import AdapterHealthStatus, InboundAdapter, InboundMessage
from app.domain.models import MailRecipient

logger = logging.getLogger(__name__)


class MailPitInboundAdapter(InboundAdapter):
    """Receive inbound mail from MailPit (local dev sandbox)."""

    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=10.0)

    async def fetch_new_messages(
        self, mailbox_id: str, since: datetime | None = None,
    ) -> list[InboundMessage]:
        """Fetch all messages from MailPit."""
        try:
            # We fetch all messages and let the caller deduplicate
            # MailPit endpoint: GET /api/v1/messages
            resp = await self.client.get(f"{self.api_url}/api/v1/messages")
            resp.raise_for_status()
            data = resp.json()
            
            # Fetch details for each message to get HTML/Text
            messages = []
            for summary in data.get("messages", []):
                msg_id = summary.get("ID")
                
                # Fetch full message
                detail_resp = await self.client.get(f"{self.api_url}/api/v1/message/{msg_id}")
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    
                    # Parse addresses
                    from_addr = detail.get("From", {})
                    from_recipient = MailRecipient(
                        email=from_addr.get("Address", "unknown@example.com"),
                        name=from_addr.get("Name", "")
                    )
                    
                    to_recipients = [
                        MailRecipient(email=addr.get("Address", ""), name=addr.get("Name", ""))
                        for addr in detail.get("To", [])
                    ]
                    cc_recipients = [
                        MailRecipient(email=addr.get("Address", ""), name=addr.get("Name", ""))
                        for addr in detail.get("Cc", [])
                    ]
                    
                    received_str = detail.get("Date")
                    try:
                        received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00")) if received_str else None
                    except Exception:
                        received_at = datetime.now()
                    
                    msg = InboundMessage(
                        provider_message_id=msg_id,
                        from_address=from_recipient.email,
                        from_name=from_recipient.name,
                        to=to_recipients,
                        cc=cc_recipients,
                        subject=detail.get("Subject", "(No Subject)"),
                        body_html=detail.get("HTML", ""),
                        body_text=detail.get("Text", ""),
                        received_at=received_at,
                    )
                    messages.append(msg)
            return messages
            
        except Exception as e:
            logger.error("Failed to fetch inbound messages from MailPit: %s", e)
            return []

    async def acknowledge(self, message_ids: list[str]) -> None:
        """Delete processed messages from MailPit so they aren't fetched again."""
        if not message_ids:
            return
        try:
            # MailPit DELETE /api/v1/messages
            # Request body: {"IDs": ["ID1", "ID2"]}
            await self.client.request(
                "DELETE", 
                f"{self.api_url}/api/v1/messages", 
                json={"IDs": message_ids}
            )
            logger.info("Acknowledged (deleted) %d messages from MailPit", len(message_ids))
        except Exception as e:
            logger.error("Failed to acknowledge messages to MailPit: %s", e)

    async def health_check(self) -> AdapterHealthStatus:
        try:
            start = datetime.now()
            resp = await self.client.get(f"{self.api_url}/api/v1/info")
            resp.raise_for_status()
            latency = (datetime.now() - start).total_seconds() * 1000
            return AdapterHealthStatus(
                name="mailpit-inbound",
                status="ok",
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            return AdapterHealthStatus(
                name="mailpit-inbound",
                status="down",
                details={"error": str(e)},
            )
            
    async def aclose(self):
        await self.client.aclose()
