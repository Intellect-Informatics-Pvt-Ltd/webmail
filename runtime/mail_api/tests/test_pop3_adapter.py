"""PSense Mail — POP3 adapter unit tests.

Tests covering:
- POP3InboundAdapter fetch, acknowledge, health_check
- MIME parser correctness
- Seen-ID deduplication store
- Pop3Config validation
- AdapterRegistry wiring
- Memory inbound adapter
"""
from __future__ import annotations

import asyncio
import email.utils
import poplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.adapters.inbound.memory import MemoryInboundAdapter
from app.adapters.inbound.mime_parser import parse_raw_message
from app.adapters.inbound.seen_store import MemorySeenStore
from app.adapters.protocols import InboundMessage
from app.domain.models import MailRecipient


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_raw_email(
    from_addr: str = "sender@example.com",
    from_name: str = "Test Sender",
    to_addr: str = "recipient@example.com",
    subject: str = "Test Subject",
    body_text: str = "Hello, world!",
    body_html: str | None = None,
    date: datetime | None = None,
) -> bytes:
    """Create a valid RFC 2822 message as raw bytes."""
    if body_html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
    else:
        msg = MIMEText(body_text, "plain")

    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(
        timeval=(date or datetime.now(timezone.utc)).timestamp(), localtime=False, usegmt=True
    )
    msg["Message-ID"] = f"<test-{id(msg)}@example.com>"
    return msg.as_bytes()


def _mock_pop3_connection(messages: list[bytes]):
    """Create a mock POP3 connection with given messages."""
    mock_conn = MagicMock()

    # UIDL response
    uidl_lines = [f"{i+1} uid-{i+1}".encode() for i in range(len(messages))]
    mock_conn.uidl.return_value = (b"+OK", uidl_lines, 0)

    # LIST response
    list_lines = [f"{i+1} {len(msg)}".encode() for i, msg in enumerate(messages)]
    mock_conn.list.return_value = (b"+OK", list_lines, 0)

    # RETR responses
    def retr_side_effect(num):
        idx = num - 1
        if 0 <= idx < len(messages):
            return (b"+OK", messages[idx].split(b"\r\n") if b"\r\n" in messages[idx] else messages[idx].split(b"\n"), len(messages[idx]))
        raise poplib.error_proto("no such message")

    mock_conn.retr.side_effect = retr_side_effect
    mock_conn.noop.return_value = b"+OK"
    mock_conn.quit.return_value = b"+OK"
    mock_conn.dele.return_value = b"+OK"

    return mock_conn


# ── Test: MIME Parser ─────────────────────────────────────────────────────────


class TestMimeParser:
    """Tests for the MIME parser utility."""

    def test_parse_simple_text_message(self):
        raw = _make_raw_email(
            from_addr="alice@example.com",
            from_name="Alice",
            subject="Hello",
            body_text="Hi there!",
        )
        msg = parse_raw_message(raw, provider_message_id="uid-1")
        assert msg.from_address == "alice@example.com"
        assert msg.from_name == "Alice"
        assert msg.subject == "Hello"
        assert msg.body_text is not None
        assert "Hi there!" in msg.body_text
        assert msg.provider_message_id == "uid-1"

    def test_parse_multipart_message(self):
        raw = _make_raw_email(
            subject="Multipart Test",
            body_text="Plain text",
            body_html="<p>HTML text</p>",
        )
        msg = parse_raw_message(raw, provider_message_id="uid-2")
        assert msg.body_text is not None
        assert "Plain text" in msg.body_text
        assert msg.body_html is not None
        assert "HTML text" in msg.body_html

    def test_parse_preserves_message_id_header(self):
        raw = _make_raw_email(subject="Headers Test")
        msg = parse_raw_message(raw, provider_message_id="uid-3")
        assert "Message-ID" in msg.raw_headers

    def test_parse_recipients(self):
        raw = _make_raw_email(to_addr="bob@example.com")
        msg = parse_raw_message(raw, provider_message_id="uid-4")
        assert len(msg.to) >= 1
        assert msg.to[0].email == "bob@example.com"

    def test_parse_date(self):
        dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        raw = _make_raw_email(date=dt)
        msg = parse_raw_message(raw, provider_message_id="uid-5")
        assert msg.received_at is not None
        assert msg.received_at.year == 2025
        assert msg.received_at.month == 6

    def test_parse_missing_date_defaults_to_now(self):
        # Create message without Date header
        text_msg = MIMEText("No date", "plain")
        text_msg["From"] = "sender@example.com"
        text_msg["To"] = "recipient@example.com"
        text_msg["Subject"] = "No Date"
        raw = text_msg.as_bytes()
        msg = parse_raw_message(raw, provider_message_id="uid-6")
        assert msg.received_at is not None
        # Should be approximately now
        assert (datetime.now(timezone.utc) - msg.received_at).total_seconds() < 5

    def test_parse_empty_body(self):
        text_msg = MIMEText("", "plain")
        text_msg["From"] = "sender@example.com"
        text_msg["To"] = "recipient@example.com"
        text_msg["Subject"] = "Empty"
        text_msg["Date"] = email.utils.formatdate(localtime=False, usegmt=True)
        raw = text_msg.as_bytes()
        msg = parse_raw_message(raw, provider_message_id="uid-7")
        assert msg.body_text is not None


# ── Test: Seen Store ──────────────────────────────────────────────────────────


class TestMemorySeenStore:
    """Tests for the in-memory deduplication store."""

    @pytest.fixture
    def store(self):
        return MemorySeenStore()

    @pytest.mark.asyncio
    async def test_empty_store_contains_nothing(self, store):
        assert await store.contains("uid-1") is False

    @pytest.mark.asyncio
    async def test_add_and_check(self, store):
        await store.add_many(["uid-1", "uid-2"])
        assert await store.contains("uid-1") is True
        assert await store.contains("uid-2") is True
        assert await store.contains("uid-3") is False

    @pytest.mark.asyncio
    async def test_contains_many(self, store):
        await store.add_many(["uid-1", "uid-2", "uid-3"])
        found = await store.contains_many(["uid-1", "uid-4", "uid-3"])
        assert found == {"uid-1", "uid-3"}

    @pytest.mark.asyncio
    async def test_remove_many(self, store):
        await store.add_many(["uid-1", "uid-2", "uid-3"])
        await store.remove_many(["uid-2"])
        assert await store.contains("uid-1") is True
        assert await store.contains("uid-2") is False
        assert await store.contains("uid-3") is True


# ── Test: Memory Inbound Adapter ──────────────────────────────────────────────


class TestMemoryInboundAdapter:
    """Tests for the MemoryInboundAdapter test stub."""

    @pytest.mark.asyncio
    async def test_empty_adapter_returns_empty(self):
        adapter = MemoryInboundAdapter()
        messages = await adapter.fetch_new_messages(mailbox_id="default")
        assert messages == []

    @pytest.mark.asyncio
    async def test_injected_messages_returned(self):
        msg = InboundMessage(
            provider_message_id="test-1",
            from_address="sender@example.com",
            from_name="Sender",
            to=[MailRecipient(email="recipient@example.com", name="Recipient")],
            cc=[],
            subject="Test",
            body_text="Hello",
        )
        adapter = MemoryInboundAdapter(messages=[msg])
        result = await adapter.fetch_new_messages(mailbox_id="default")
        assert len(result) == 1
        assert result[0].subject == "Test"

    @pytest.mark.asyncio
    async def test_acknowledge_removes_messages(self):
        msg = InboundMessage(
            provider_message_id="test-1",
            from_address="sender@example.com",
            from_name="Sender",
            to=[],
            cc=[],
            subject="Test",
        )
        adapter = MemoryInboundAdapter(messages=[msg])
        await adapter.acknowledge(["test-1"])
        result = await adapter.fetch_new_messages(mailbox_id="default")
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self):
        adapter = MemoryInboundAdapter()
        status = await adapter.health_check()
        assert status.name == "memory-inbound"
        assert status.status == "ok"
        assert status.latency_ms == 0.0


# ── Test: Pop3Config Validation ───────────────────────────────────────────────


class TestPop3ConfigValidation:
    """Tests for Pop3Config field validation."""

    def test_valid_config(self):
        from config.settings import Pop3Config
        cfg = Pop3Config(host="mail.example.com", port=995, username="user", password="pass")
        assert cfg.host == "mail.example.com"
        assert cfg.port == 995

    def test_port_zero_raises_validation_error(self):
        from config.settings import Pop3Config
        with pytest.raises(ValidationError):
            Pop3Config(port=0)

    def test_port_too_high_raises_validation_error(self):
        from config.settings import Pop3Config
        with pytest.raises(ValidationError):
            Pop3Config(port=70000)

    def test_connect_timeout_zero_raises_validation_error(self):
        from config.settings import Pop3Config
        with pytest.raises(ValidationError):
            Pop3Config(connect_timeout_seconds=0)

    def test_max_messages_zero_raises_validation_error(self):
        from config.settings import Pop3Config
        with pytest.raises(ValidationError):
            Pop3Config(max_messages_per_poll=0)

    def test_max_messages_too_high_raises_validation_error(self):
        from config.settings import Pop3Config
        with pytest.raises(ValidationError):
            Pop3Config(max_messages_per_poll=501)

    def test_invalid_tls_mode_raises_validation_error(self):
        from config.settings import Pop3Config
        with pytest.raises(ValidationError):
            Pop3Config(tls_mode="invalid")


# ── Test: POP3 Adapter (mocked poplib) ───────────────────────────────────────


class TestPOP3InboundAdapter:
    """Tests for POP3InboundAdapter with mocked poplib."""

    @pytest.fixture
    def config(self):
        from config.settings import Pop3Config
        return Pop3Config(
            host="localhost",
            port=1110,
            username="testuser",
            password="testpass",
            tls_mode="none",
        )

    @pytest.mark.asyncio
    async def test_fetch_empty_server(self, config):
        from app.adapters.inbound.pop3 import POP3InboundAdapter

        mock_conn = _mock_pop3_connection([])
        store = MemorySeenStore()
        adapter = POP3InboundAdapter(config=config, seen_store=store)

        with patch("app.adapters.inbound.pop3.POP3InboundAdapter._connect", return_value=mock_conn):
            messages = await adapter.fetch_new_messages(mailbox_id="default")

        assert messages == []

    @pytest.mark.asyncio
    async def test_fetch_two_messages(self, config):
        from app.adapters.inbound.pop3 import POP3InboundAdapter

        raw1 = _make_raw_email(from_addr="alice@example.com", subject="First")
        raw2 = _make_raw_email(from_addr="bob@example.com", subject="Second")
        mock_conn = _mock_pop3_connection([raw1, raw2])
        store = MemorySeenStore()
        adapter = POP3InboundAdapter(config=config, seen_store=store)

        with patch("app.adapters.inbound.pop3.POP3InboundAdapter._connect", return_value=mock_conn):
            messages = await adapter.fetch_new_messages(mailbox_id="default")

        assert len(messages) == 2
        assert messages[0].from_address == "alice@example.com"
        assert messages[0].subject == "First"
        assert messages[1].from_address == "bob@example.com"
        assert messages[1].subject == "Second"

    @pytest.mark.asyncio
    async def test_deduplication_second_call_empty(self, config):
        from app.adapters.inbound.pop3 import POP3InboundAdapter

        raw1 = _make_raw_email(subject="Dedup Test")
        mock_conn = _mock_pop3_connection([raw1])
        store = MemorySeenStore()
        adapter = POP3InboundAdapter(config=config, seen_store=store)

        with patch("app.adapters.inbound.pop3.POP3InboundAdapter._connect", return_value=mock_conn):
            first = await adapter.fetch_new_messages(mailbox_id="default")
            assert len(first) == 1

            # Second call with same server state → empty (deduplicated)
            second = await adapter.fetch_new_messages(mailbox_id="default")
            assert len(second) == 0

    @pytest.mark.asyncio
    async def test_acknowledge_issues_dele(self, config):
        from app.adapters.inbound.pop3 import POP3InboundAdapter

        raw1 = _make_raw_email(subject="Ack Test")
        mock_conn = _mock_pop3_connection([raw1])
        store = MemorySeenStore()
        await store.add_many(["uid-1"])
        adapter = POP3InboundAdapter(config=config, seen_store=store)

        with patch("app.adapters.inbound.pop3.POP3InboundAdapter._connect", return_value=mock_conn):
            await adapter.acknowledge(["uid-1"])

        mock_conn.dele.assert_called_once_with(1)
        mock_conn.quit.assert_called()
        # Should be removed from seen store
        assert await store.contains("uid-1") is False

    @pytest.mark.asyncio
    async def test_health_check_ok(self, config):
        from app.adapters.inbound.pop3 import POP3InboundAdapter

        mock_conn = MagicMock()
        mock_conn.noop.return_value = b"+OK"
        mock_conn.quit.return_value = b"+OK"
        store = MemorySeenStore()
        adapter = POP3InboundAdapter(config=config, seen_store=store)

        with patch("app.adapters.inbound.pop3.POP3InboundAdapter._connect", return_value=mock_conn):
            status = await adapter.health_check()

        assert status.name == "pop3-inbound"
        assert status.status == "ok"
        assert status.latency_ms is not None
        assert status.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_health_check_down_on_connection_failure(self, config):
        from app.adapters.inbound.pop3 import POP3InboundAdapter

        store = MemorySeenStore()
        adapter = POP3InboundAdapter(config=config, seen_store=store)

        with patch(
            "app.adapters.inbound.pop3.POP3InboundAdapter._connect",
            side_effect=OSError("Connection refused"),
        ):
            status = await adapter.health_check()

        assert status.name == "pop3-inbound"
        assert status.status == "down"
        assert "error" in status.details


# ── Test: AdapterRegistry ─────────────────────────────────────────────────────


class TestAdapterRegistryInbound:
    """Tests for AdapterRegistry.inbound property."""

    def test_pop3_provider_returns_pop3_adapter(self):
        from app.adapters.registry import AdapterRegistry
        from config.settings import Pop3Config, ProviderConfig, Settings

        # Create minimal settings mock
        settings = MagicMock(spec=Settings)
        settings.provider = MagicMock(spec=ProviderConfig)
        settings.provider.active = "pop3"
        settings.provider.pop3 = Pop3Config(
            host="localhost", port=1110, username="user", password="pass"
        )
        settings.database = MagicMock()
        settings.database.backend = "memory"

        registry = AdapterRegistry(settings)
        adapter = registry.inbound

        from app.adapters.inbound.pop3 import POP3InboundAdapter
        assert isinstance(adapter, POP3InboundAdapter)

    def test_memory_provider_returns_memory_adapter(self):
        from app.adapters.registry import AdapterRegistry
        from config.settings import Settings

        settings = MagicMock(spec=Settings)
        settings.provider = MagicMock()
        settings.provider.active = "memory"

        registry = AdapterRegistry(settings)
        adapter = registry.inbound

        from app.adapters.inbound.memory import MemoryInboundAdapter
        assert isinstance(adapter, MemoryInboundAdapter)

    def test_pop3_without_username_raises_value_error(self):
        from app.adapters.registry import AdapterRegistry
        from config.settings import Pop3Config, Settings

        settings = MagicMock(spec=Settings)
        settings.provider = MagicMock()
        settings.provider.active = "pop3"
        settings.provider.pop3 = Pop3Config(host="localhost", username="")
        settings.database = MagicMock()
        settings.database.backend = "memory"

        registry = AdapterRegistry(settings)
        with pytest.raises(ValueError, match="username is required"):
            _ = registry.inbound


# ── Test: MIME Parser Robustness ──────────────────────────────────────────────


class TestMimeParserRobustness:
    """Robustness tests — the parser must never crash on valid-ish input."""

    def test_garbage_bytes_dont_crash(self):
        """Parser should handle arbitrary bytes without raising."""
        garbage = b"Not a valid email at all\r\nJust random bytes\r\n"
        # Should not raise
        msg = parse_raw_message(garbage, provider_message_id="garbage-1")
        assert msg.provider_message_id == "garbage-1"

    def test_binary_attachment_doesnt_crash(self):
        """Parser handles messages with binary attachments."""
        from email.mime.base import MIMEBase
        from email import encoders

        outer = MIMEMultipart()
        outer["From"] = "sender@example.com"
        outer["To"] = "recipient@example.com"
        outer["Subject"] = "With attachment"
        outer["Date"] = email.utils.formatdate(localtime=False, usegmt=True)
        outer.attach(MIMEText("See attached", "plain"))

        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(b"\x00\x01\x02\x03" * 100)
        encoders.encode_base64(attachment)
        attachment.add_header("Content-Disposition", "attachment", filename="test.bin")
        outer.attach(attachment)

        raw = outer.as_bytes()
        msg = parse_raw_message(raw, provider_message_id="binary-1")
        assert len(msg.attachments) == 1
        assert msg.attachments[0]["name"] == "test.bin"
        assert msg.attachments[0]["mime"] == "application/octet-stream"

    def test_encoded_subject(self):
        """Parser handles RFC 2047 encoded subjects."""
        from email.mime.text import MIMEText
        import email.charset

        text_msg = MIMEText("Body", "plain", "utf-8")
        text_msg["From"] = "sender@example.com"
        text_msg["To"] = "recipient@example.com"
        # RFC 2047 encoded subject
        text_msg["Subject"] = "=?UTF-8?B?SGVsbG8gV29ybGQ=?="
        text_msg["Date"] = email.utils.formatdate(localtime=False, usegmt=True)

        raw = text_msg.as_bytes()
        msg = parse_raw_message(raw, provider_message_id="encoded-1")
        assert "Hello World" in msg.subject
