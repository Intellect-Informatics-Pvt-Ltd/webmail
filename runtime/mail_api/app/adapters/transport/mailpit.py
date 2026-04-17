"""PSense Mail — MailPit SMTP transport adapter.

Sends outbound mail via aiosmtplib to a MailPit instance.
MailPit captures all sent mail in a dev-friendly web UI (port 8025).

Includes retry with exponential backoff for transient SMTP failures.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

from app.adapters.protocols import AdapterHealthStatus, OutboundMessage, TransportReceipt

logger = logging.getLogger(__name__)

# Retry configuration
_SMTP_MAX_RETRIES = 3
_SMTP_RETRY_BASE_DELAY = 1.0  # seconds


class MailpitTransportAdapter:
    """SMTP transport adapter targeting MailPit with retry logic."""

    def __init__(self, smtp_host: str, smtp_port: int, from_address: str):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._from_address = from_address
        logger.info("MailPit transport: %s:%d", smtp_host, smtp_port)

    async def send(self, message: OutboundMessage) -> TransportReceipt:
        """Send a message via SMTP to MailPit with retry on transient failures."""
        import aiosmtplib

        msg = self._build_email(message)

        last_exc: Exception | None = None
        for attempt in range(_SMTP_MAX_RETRIES):
            try:
                await aiosmtplib.send(
                    msg,
                    hostname=self._smtp_host,
                    port=self._smtp_port,
                    use_tls=False,
                    start_tls=False,
                )
                logger.info("MailPit: sent message %s (attempt %d)", message.message_id, attempt + 1)
                return TransportReceipt(
                    transport_message_id=msg["Message-ID"],
                    accepted_at=datetime.now(timezone.utc),
                )
            except (aiosmtplib.SMTPConnectError, aiosmtplib.SMTPServerDisconnected, ConnectionError, OSError) as e:
                last_exc = e
                if attempt < _SMTP_MAX_RETRIES - 1:
                    wait = _SMTP_RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "MailPit: SMTP connection failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, _SMTP_MAX_RETRIES, wait, e,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("MailPit: SMTP failed after %d attempts: %s", _SMTP_MAX_RETRIES, e)
            except Exception as e:
                # Non-retryable error — fail immediately
                logger.error("MailPit send failed (non-retryable): %s", e)
                from app.domain.errors import PermanentDeliveryError
                raise PermanentDeliveryError(message.message_id, str(e)) from e

        # All retries exhausted — raise retryable
        from app.domain.errors import RetryableDeliveryError
        raise RetryableDeliveryError(message.message_id, str(last_exc)) from last_exc

    def _build_email(self, message: OutboundMessage) -> EmailMessage:
        """Build a stdlib EmailMessage from an OutboundMessage."""
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

        return msg

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
