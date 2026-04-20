"""PSense Mail — IMAP inbound adapter.

Connects to an IMAP server via aioimaplib, fetches new messages from
a configured mailbox, and returns them as InboundMessage objects.
"""
from __future__ import annotations

import asyncio
import email
import email.policy
import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.adapters.protocols import AdapterHealthStatus, InboundAdapter, InboundMessage
from app.domain.models import MailRecipient

logger = logging.getLogger(__name__)


def _parse_address(addr: str) -> tuple[str, str]:
    """Parse 'Name <email>' into (name, email)."""
    if "<" in addr and ">" in addr:
        parts = addr.rsplit("<", 1)
        name = parts[0].strip().strip('"')
        email_addr = parts[1].rstrip(">").strip()
        return name, email_addr
    return "", addr.strip()


def _parse_recipients(header: str | None) -> list[MailRecipient]:
    """Parse comma-separated address header."""
    if not header:
        return []
    recipients = []
    for addr in header.split(","):
        addr = addr.strip()
        if addr:
            name, email_addr = _parse_address(addr)
            recipients.append(MailRecipient(email=email_addr, name=name))
    return recipients


class IMAPInboundAdapter:
    """IMAP inbound adapter using standard imaplib (sync, run in executor)."""

    def __init__(
        self, host: str, port: int = 993,
        username: str = "", password: str = "",
        tls_mode: str = "ssl", mailbox: str = "INBOX",
        connect_timeout: int = 10,
    ):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._tls_mode = tls_mode
        self._mailbox = mailbox
        self._timeout = connect_timeout

    async def fetch_new_messages(
        self, mailbox_id: str, since: datetime | None = None,
    ) -> list[InboundMessage]:
        """Fetch unseen messages from the IMAP mailbox."""
        import imaplib

        loop = asyncio.get_event_loop()
        messages = await loop.run_in_executor(
            None, self._fetch_sync, since,
        )
        return messages

    def _fetch_sync(self, since: datetime | None) -> list[InboundMessage]:
        """Synchronous IMAP fetch — runs in executor."""
        import imaplib

        try:
            if self._tls_mode == "ssl":
                conn = imaplib.IMAP4_SSL(self._host, self._port, timeout=self._timeout)
            else:
                conn = imaplib.IMAP4(self._host, self._port, timeout=self._timeout)
                if self._tls_mode == "starttls":
                    conn.starttls()

            conn.login(self._username, self._password)
            conn.select(self._mailbox)

            # Search for unseen messages
            search_criteria = "UNSEEN"
            if since:
                date_str = since.strftime("%d-%b-%Y")
                search_criteria = f'(UNSEEN SINCE {date_str})'

            _, msg_ids = conn.search(None, search_criteria)
            if not msg_ids[0]:
                conn.close()
                conn.logout()
                return []

            messages: list[InboundMessage] = []
            for num in msg_ids[0].split()[:50]:  # Limit per poll
                _, data = conn.fetch(num, "(RFC822)")
                if not data or not data[0]:
                    continue
                raw = data[0][1] if isinstance(data[0], tuple) else data[0]
                msg = email.message_from_bytes(raw, policy=email.policy.default)

                # Extract body
                body_html = None
                body_text = None
                if msg.is_multipart():
                    for part in msg.walk():
                        ct = part.get_content_type()
                        if ct == "text/plain" and not body_text:
                            body_text = part.get_content()
                        elif ct == "text/html" and not body_html:
                            body_html = part.get_content()
                else:
                    ct = msg.get_content_type()
                    content = msg.get_content()
                    if ct == "text/html":
                        body_html = content
                    else:
                        body_text = content

                from_name, from_addr = _parse_address(msg.get("From", ""))
                messages.append(InboundMessage(
                    provider_message_id=num.decode() if isinstance(num, bytes) else str(num),
                    from_address=from_addr,
                    from_name=from_name,
                    to=_parse_recipients(msg.get("To")),
                    cc=_parse_recipients(msg.get("Cc")),
                    subject=msg.get("Subject", ""),
                    body_html=body_html,
                    body_text=body_text,
                    received_at=datetime.now(timezone.utc),
                    raw_headers={
                        "Message-ID": msg.get("Message-ID", ""),
                        "In-Reply-To": msg.get("In-Reply-To", ""),
                        "References": msg.get("References", ""),
                    },
                ))

            conn.close()
            conn.logout()
            return messages

        except Exception as exc:
            logger.error("IMAP fetch failed: %s", exc)
            raise

    async def acknowledge(self, message_ids: list[str]) -> None:
        """Mark messages as seen on IMAP server."""
        import imaplib

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._ack_sync, message_ids)

    def _ack_sync(self, message_ids: list[str]) -> None:
        import imaplib

        try:
            if self._tls_mode == "ssl":
                conn = imaplib.IMAP4_SSL(self._host, self._port, timeout=self._timeout)
            else:
                conn = imaplib.IMAP4(self._host, self._port, timeout=self._timeout)
                if self._tls_mode == "starttls":
                    conn.starttls()

            conn.login(self._username, self._password)
            conn.select(self._mailbox)

            for mid in message_ids:
                conn.store(mid.encode() if isinstance(mid, str) else mid, "+FLAGS", "\\Seen")

            conn.close()
            conn.logout()
        except Exception as exc:
            logger.error("IMAP acknowledge failed: %s", exc)

    async def health_check(self) -> AdapterHealthStatus:
        try:
            import imaplib
            start = time.monotonic()
            loop = asyncio.get_event_loop()

            def _check():
                if self._tls_mode == "ssl":
                    conn = imaplib.IMAP4_SSL(self._host, self._port, timeout=5)
                else:
                    conn = imaplib.IMAP4(self._host, self._port, timeout=5)
                conn.login(self._username, self._password)
                conn.logout()

            await loop.run_in_executor(None, _check)
            latency = (time.monotonic() - start) * 1000
            return AdapterHealthStatus(name="imap_inbound", status="ok", latency_ms=latency)
        except Exception as exc:
            return AdapterHealthStatus(
                name="imap_inbound", status="down",
                details={"error": str(exc)},
            )
