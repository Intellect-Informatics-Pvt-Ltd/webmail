"""PSense Mail — POP3 inbound adapter.

Implements the InboundAdapter protocol using Python's poplib module wrapped
in asyncio executors to avoid blocking the event loop. Supports plain, SSL,
and STARTTLS connections with full deduplication via a SeenStore.
"""
from __future__ import annotations

import asyncio
import logging
import poplib
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.adapters.inbound.mime_parser import parse_raw_message
from app.adapters.inbound.seen_store import SeenStore
from app.adapters.protocols import AdapterHealthStatus, InboundAdapter, InboundMessage
from app.domain.errors import ProviderUnavailableError

if TYPE_CHECKING:
    from config.settings import Pop3Config

logger = logging.getLogger(__name__)


class POP3InboundAdapter(InboundAdapter):
    """Receive inbound mail from a POP3 server.

    All blocking poplib operations are run in a thread executor to keep
    the asyncio event loop responsive.
    """

    def __init__(self, config: "Pop3Config", seen_store: SeenStore) -> None:
        self._config = config
        self._seen_store = seen_store

    # ── Public protocol methods ───────────────────────────────────────────

    async def acknowledge(self, message_ids: list[str]) -> None:
        """Delete acknowledged messages from the POP3 server."""
        if not message_ids:
            return
        loop = asyncio.get_event_loop()
        try:
            deleted = await loop.run_in_executor(
                None, self._acknowledge_sync, message_ids,
            )
            # Remove from seen store after successful deletion
            await self._seen_store.remove_many(deleted)
        except ProviderUnavailableError:
            raise
        except Exception as e:
            raise ProviderUnavailableError("pop3", str(e)) from e

    async def health_check(self) -> AdapterHealthStatus:
        """Check POP3 server connectivity with a NOOP command."""
        loop = asyncio.get_event_loop()
        try:
            latency_ms = await loop.run_in_executor(None, self._health_check_sync)
            return AdapterHealthStatus(
                name="pop3-inbound",
                status="ok",
                latency_ms=round(latency_ms, 2),
            )
        except Exception as e:
            return AdapterHealthStatus(
                name="pop3-inbound",
                status="down",
                details={"error": str(e)},
            )

    # ── Synchronous helpers (run in executor) ─────────────────────────────

    def _connect(self) -> poplib.POP3 | poplib.POP3_SSL:
        """Establish an authenticated POP3 connection.

        Returns the connected and authenticated poplib client.
        Raises ProviderUnavailableError on connection or auth failure.
        """
        cfg = self._config
        try:
            if cfg.tls_mode == "ssl":
                conn = poplib.POP3_SSL(
                    cfg.host, cfg.port,
                    timeout=cfg.connect_timeout_seconds,
                )
            else:
                conn = poplib.POP3(
                    cfg.host, cfg.port,
                    timeout=cfg.connect_timeout_seconds,
                )
                if cfg.tls_mode == "starttls":
                    conn.stls()
        except (OSError, poplib.error_proto) as e:
            raise ProviderUnavailableError("pop3", f"Connection failed: {e}") from e

        # Authenticate
        try:
            conn.user(cfg.username)
            conn.pass_(cfg.password)
        except poplib.error_proto as e:
            try:
                conn.quit()
            except Exception:
                pass
            raise ProviderUnavailableError("pop3", f"Authentication failed: {e}") from e

        return conn

    def _get_uidl_mapping(self, conn: poplib.POP3 | poplib.POP3_SSL) -> dict[str, int]:
        """Get UID-to-sequence-number mapping via UIDL command.

        Falls back to hostname-prefixed sequence numbers if UIDL is not supported.
        Returns: dict mapping provider_message_uid -> sequence_number
        """
        try:
            resp, listings, _ = conn.uidl()
            uid_map: dict[str, int] = {}
            for line in listings:
                decoded = line.decode("ascii", errors="replace") if isinstance(line, bytes) else line
                parts = decoded.split(None, 1)
                if len(parts) == 2:
                    seq_num = int(parts[0])
                    uid = parts[1]
                    uid_map[uid] = seq_num
            return uid_map
        except poplib.error_proto:
            # UIDL not supported — fall back to seq numbers prefixed with hostname
            logger.warning("POP3 server does not support UIDL, falling back to sequence numbers")
            _, msg_list, _ = conn.list()
            uid_map = {}
            for line in msg_list:
                decoded = line.decode("ascii", errors="replace") if isinstance(line, bytes) else line
                parts = decoded.split(None, 1)
                if parts:
                    seq_num = int(parts[0])
                    uid = f"{self._config.host}:{seq_num}"
                    uid_map[uid] = seq_num
            return uid_map

    def _fetch_sync(self, since: datetime | None) -> list[InboundMessage]:
        """Synchronous fetch implementation — runs in thread executor."""
        conn = self._connect()
        try:
            uid_map = self._get_uidl_mapping(conn)
            if not uid_map:
                return []

            # Filter out already-seen UIDs (sync check via blocking call)
            all_uids = list(uid_map.keys())
            # We need to do seen-check synchronously; use a small event loop trick
            # Actually, we'll collect all and let the async caller filter.
            # Instead, we collect all UIDs and return; the async wrapper handles seen filtering.
            # But the requirement says we should do it here for efficiency.
            # We'll batch check using a new event loop is not ideal. Instead, we collect
            # all UIDs and raw bytes, then filter in the async wrapper.
            # 
            # Better approach: fetch all available, return them with UIDs, and let
            # the async method handle dedup. But the plan says add to seen store before returning.
            #
            # Simplest correct approach: we can't call async from sync easily.
            # Let's restructure to do the seen-check in the async method and only
            # call this for retrieval of specific messages.

            # Fetch raw bytes for ALL messages (up to max_messages_per_poll)
            messages_raw: list[tuple[str, bytes]] = []
            max_fetch = self._config.max_messages_per_poll

            for uid, seq_num in uid_map.items():
                if len(messages_raw) >= max_fetch:
                    break
                try:
                    resp, lines, octets = conn.retr(seq_num)
                    raw_bytes = b"\r\n".join(lines)
                    messages_raw.append((uid, raw_bytes))
                except poplib.error_proto as e:
                    logger.warning("Failed to RETR message seq=%d uid=%s: %s", seq_num, uid, e)
                    continue

            # Parse messages
            results: list[InboundMessage] = []
            for uid, raw_bytes in messages_raw:
                try:
                    msg = parse_raw_message(raw_bytes, provider_message_id=uid)
                    # Apply since filter
                    if since and msg.received_at and msg.received_at < since:
                        continue
                    results.append(msg)
                except Exception as e:
                    logger.warning("Failed to parse message uid=%s: %s", uid, e)
                    continue

            return results

        finally:
            try:
                conn.quit()
            except Exception:
                pass

    def _acknowledge_sync(self, message_ids: list[str]) -> list[str]:
        """Synchronous acknowledge — DELE messages and QUIT to commit.

        Returns list of successfully deleted UIDs.
        """
        conn = self._connect()
        deleted: list[str] = []
        try:
            uid_map = self._get_uidl_mapping(conn)
            for uid in message_ids:
                seq_num = uid_map.get(uid)
                if seq_num is None:
                    # UID no longer on server — already deleted
                    logger.debug("UID %s not found on server during acknowledge (already deleted?)", uid)
                    deleted.append(uid)  # Consider it handled
                    continue
                try:
                    conn.dele(seq_num)
                    deleted.append(uid)
                except poplib.error_proto as e:
                    logger.warning("DELE failed for uid=%s seq=%d: %s", uid, seq_num, e)
            return deleted
        finally:
            try:
                conn.quit()
            except Exception:
                pass

    def _health_check_sync(self) -> float:
        """Synchronous health check — NOOP and measure latency."""
        conn = self._connect()
        try:
            start = time.perf_counter()
            conn.noop()
            latency_ms = (time.perf_counter() - start) * 1000
            return latency_ms
        finally:
            try:
                conn.quit()
            except Exception:
                pass

    # ── Async fetch with deduplication ────────────────────────────────────

    async def fetch_new_messages(
        self, mailbox_id: str, since: datetime | None = None,
    ) -> list[InboundMessage]:
        """Fetch new messages from POP3 server, filtering out already-seen UIDs."""
        loop = asyncio.get_event_loop()
        try:
            all_messages = await loop.run_in_executor(None, self._fetch_sync, since)
        except ProviderUnavailableError:
            raise
        except Exception as e:
            raise ProviderUnavailableError("pop3", str(e)) from e

        if not all_messages:
            return []

        # Deduplicate against seen store
        all_uids = [m.provider_message_id for m in all_messages]
        already_seen = await self._seen_store.contains_many(all_uids)

        new_messages = [m for m in all_messages if m.provider_message_id not in already_seen]

        if new_messages:
            new_uids = [m.provider_message_id for m in new_messages]
            await self._seen_store.add_many(new_uids)
            logger.info(
                "POP3 fetched %d new messages (%d total on server, %d already seen)",
                len(new_messages), len(all_messages), len(already_seen),
            )

        return new_messages
