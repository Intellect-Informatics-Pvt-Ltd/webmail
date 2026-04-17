"""PSense Mail — MailPit SMTP transport adapter.

Sends outbound mail via aiosmtplib to a MailPit instance.
MailPit captures all sent mail in a dev-friendly web UI (port 8025).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

from app.adapters.protocols import AdapterHealthStatus, OutboundMessage, TransportReceipt

logger = logging.getLogger(__name__)


class MailpitTransportAdapter:
    """SMTP transport adapter targeting MailPit."""

    def __init__(self, smtp_host: str, smtp_port: int, from_address: str):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._from_address = from_address
        logger.info("MailPit transport: %s:%d", smtp_host, smtp_port)

    async def send(self, message: OutboundMessage) -> TransportReceipt:
        """Send a message via SMTP to MailPit."""
        import aiosmtplib

        msg = EmailMessage()
        msg["From"] = f"{message.from_name} <{message.from_address or self._from_address}>"
        msg["To"] = ", ".join(f"{r.name} <{r.email}>" if r.name else r.email for r in message.to)
        if message.cc:
            msg["Cc"] = ", ".join(f"{r.name} <{r.email}>" if r.name else r.email for r in message.cc)
        msg["Subject"] = message.subject
        msg["Message-ID"] = f"<{message.message_id}@psense.local>"

        for header_key, header_val in message.headers.items():
            msg[header_key] = header_val

        if message.body_html:
            msg.set_content(message.body_text or "")
            msg.add_alternative(message.body_html, subtype="html")
        elif message.body_text:
            msg.set_content(message.body_text)
        else:
            msg.set_content("")

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._smtp_host,
                port=self._smtp_port,
                use_tls=False,
                start_tls=False,
            )
            logger.info("MailPit: sent message %s", message.message_id)
            return TransportReceipt(
                transport_message_id=msg["Message-ID"],
                accepted_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error("MailPit send failed: %s", e)
            from app.domain.errors import RetryableDeliveryError
            raise RetryableDeliveryError(message.message_id, str(e)) from e

    async def health_check(self) -> AdapterHealthStatus:
        """Check SMTP connectivity."""
        import aiosmtplib

        start = time.monotonic()
        try:
            smtp = aiosmtplib.SMTP(hostname=self._smtp_host, port=self._smtp_port)
            await smtp.connect()
            await smtp.quit()
            latency = (time.monotonic() - start) * 1000
            return AdapterHealthStatus(name="mailpit-smtp", status="ok", latency_ms=round(latency, 2))
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return AdapterHealthStatus(
                name="mailpit-smtp", status="down",
                latency_ms=round(latency, 2),
                details={"error": str(e)},
            )
