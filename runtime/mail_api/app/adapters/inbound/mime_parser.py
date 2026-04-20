"""PSense Mail — RFC 2822 MIME parser utility.

Parses raw email bytes into a normalized InboundMessage suitable for
ingestion by the InboundPollerWorker. Handles multipart messages,
charset decoding fallbacks, attachment extraction, and header preservation.
"""
from __future__ import annotations

import email
import email.header
import email.policy
import email.utils
import logging
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

from app.adapters.protocols import InboundMessage
from app.domain.models import MailRecipient

logger = logging.getLogger(__name__)

# Headers we always preserve for thread resolution and diagnostics
_PRESERVED_HEADERS = frozenset({
    "Message-ID", "In-Reply-To", "References",
    "Content-Type", "MIME-Version", "X-Mailer",
})


def parse_raw_message(raw: bytes, provider_message_id: str) -> InboundMessage:
    """Parse raw RFC 2822 message bytes into an InboundMessage.

    Args:
        raw: The raw message bytes as retrieved from the mail server.
        provider_message_id: The unique ID assigned by the provider (e.g. POP3 UIDL).

    Returns:
        A fully populated InboundMessage instance.
    """
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    assert isinstance(msg, EmailMessage)

    # ── From ──────────────────────────────────────────────────────────────
    from_name, from_address = _parse_from(msg)

    # ── To / Cc ───────────────────────────────────────────────────────────
    to_recipients = _parse_address_list(msg.get("To", ""))
    cc_recipients = _parse_address_list(msg.get("Cc", ""))

    # ── Subject ───────────────────────────────────────────────────────────
    subject = _decode_subject(msg.get("Subject", ""))

    # ── Date ──────────────────────────────────────────────────────────────
    received_at = _parse_date(msg.get("Date"))

    # ── Body and attachments ──────────────────────────────────────────────
    body_text: str | None = None
    body_html: str | None = None
    attachments: list[dict[str, Any]] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            # Skip multipart containers
            if part.get_content_maintype() == "multipart":
                continue

            # Attachment detection: explicit disposition or non-text type without inline
            is_attachment = (
                "attachment" in disposition
                or (content_type not in ("text/plain", "text/html") and "inline" not in disposition)
            )

            if is_attachment:
                _extract_attachment(part, attachments)
            elif content_type == "text/plain" and body_text is None:
                body_text = _decode_payload(part)
            elif content_type == "text/html" and body_html is None:
                body_html = _decode_payload(part)
    else:
        content_type = msg.get_content_type()
        if content_type == "text/html":
            body_html = _decode_payload(msg)
        else:
            body_text = _decode_payload(msg)

    # ── Raw headers ───────────────────────────────────────────────────────
    raw_headers = _extract_headers(msg)

    return InboundMessage(
        provider_message_id=provider_message_id,
        from_address=from_address,
        from_name=from_name,
        to=to_recipients,
        cc=cc_recipients,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        received_at=received_at,
        attachments=attachments,
        raw_headers=raw_headers,
    )


# ── Internal helpers ──────────────────────────────────────────────────────────


def _parse_from(msg: EmailMessage) -> tuple[str, str]:
    """Extract display name and email from the From header."""
    from_header = msg.get("From", "")
    name, addr = email.utils.parseaddr(from_header)
    return name, addr


def _parse_address_list(header_value: str) -> list[MailRecipient]:
    """Parse a To or Cc header into a list of MailRecipient objects."""
    if not header_value:
        return []
    addresses = email.utils.getaddresses([header_value])
    return [
        MailRecipient(email=addr, name=name)
        for name, addr in addresses
        if addr  # skip entries with empty address
    ]


def _decode_subject(raw_subject: str) -> str:
    """Decode RFC 2047 encoded-word sequences in a subject line."""
    if not raw_subject:
        return ""
    parts = email.header.decode_header(raw_subject)
    decoded_parts: list[str] = []
    for data, charset in parts:
        if isinstance(data, bytes):
            try:
                decoded_parts.append(data.decode(charset or "utf-8"))
            except (UnicodeDecodeError, LookupError):
                decoded_parts.append(data.decode("latin-1", errors="replace"))
        else:
            decoded_parts.append(data)
    return "".join(decoded_parts)


def _parse_date(date_str: str | None) -> datetime:
    """Parse a Date header, falling back to UTC now on failure."""
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError, OverflowError):
        return datetime.now(timezone.utc)


def _decode_payload(part: EmailMessage) -> str:
    """Decode a MIME part's payload to a string with charset fallback."""
    try:
        payload = part.get_content()
        if isinstance(payload, str):
            return payload
        if isinstance(payload, bytes):
            charset = part.get_content_charset() or "utf-8"
            try:
                return payload.decode(charset)
            except (UnicodeDecodeError, LookupError):
                return payload.decode("latin-1", errors="replace")
        return str(payload) if payload else ""
    except Exception:
        # Last resort: try raw payload bytes
        raw = part.get_payload(decode=True)
        if isinstance(raw, bytes):
            return raw.decode("latin-1", errors="replace")
        return ""


def _extract_attachment(part: EmailMessage, attachments: list[dict[str, Any]]) -> None:
    """Extract attachment metadata and content from a MIME part."""
    filename = part.get_filename() or "unnamed"
    content_type = part.get_content_type()
    payload = part.get_payload(decode=True)
    if payload is None:
        payload = b""

    attachments.append({
        "name": filename,
        "mime": content_type,
        "size": len(payload),
        "content": payload,
    })


def _extract_headers(msg: EmailMessage) -> dict[str, str]:
    """Extract raw header values, always including thread-resolution headers."""
    headers: dict[str, str] = {}
    for key in msg.keys():
        if key in _PRESERVED_HEADERS or key.startswith("X-"):
            value = msg.get(key, "")
            if isinstance(value, str):
                headers[key] = value
    # Always ensure these are present (even if empty)
    for key in ("Message-ID", "In-Reply-To", "References"):
        if key not in headers:
            val = msg.get(key, "")
            if val:
                headers[key] = val
    return headers
