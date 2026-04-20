"""PSense Mail — Inbound Poller Worker.

Polls the inbound adapter for new messages, resolves thread membership
using In-Reply-To / References headers (falling back to subject+participant
matching), and evaluates mail rules on each new message.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

from ulid import ULID

from app.adapters.protocols import InboundAdapter, InboundMessage
from app.domain.models import MailRecipient, MessageDoc, ThreadDoc

logger = logging.getLogger(__name__)

# Pattern to strip Re:/Fwd: prefixes for subject-based thread matching
_SUBJECT_STRIP_RE = re.compile(r"^(?:(?:Re|Fwd|Fw)\s*:\s*)+", re.IGNORECASE)


def _normalize_subject(subject: str) -> str:
    """Strip Re:/Fwd: prefixes and whitespace for thread matching."""
    return _SUBJECT_STRIP_RE.sub("", subject).strip().lower()


class InboundPollerWorker:
    """Worker that periodically polls for inbound messages."""

    def __init__(self, adapter: InboundAdapter, cache_user_id: str, poll_interval: int = 15):
        self.adapter = adapter
        self.interval = poll_interval
        self._running = False
        self._task: asyncio.Task | None = None
        self.user_id = cache_user_id

        # Status tracking for /accounts/pop3/status endpoint
        self.last_poll_at: datetime | None = None
        self.last_poll_status: str = "never"  # "ok" | "error" | "never"
        self.last_error: str | None = None
        self.messages_last_cycle: int = 0
        self.is_polling: bool = False

        # Immediate poll trigger
        self._trigger_event: asyncio.Event | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._trigger_event = asyncio.Event()
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Inbound poller worker started (interval=%ds)", self.interval)

    def stop(self) -> None:
        self._running = False
        if self._trigger_event:
            self._trigger_event.set()  # Wake up sleeping loop
        if self._task:
            self._task.cancel()
        logger.info("Inbound poller worker stopped")

    def trigger_immediate_poll(self) -> None:
        """Wake the poller to perform an immediate out-of-cycle fetch."""
        if self._trigger_event:
            self._trigger_event.set()

    async def _poll_loop(self) -> None:
        from app.services.rules_facade import RulesFacade

        rules_facade = RulesFacade()

        while self._running:
            self.is_polling = True
            try:
                # Fetch new messages
                messages = await self.adapter.fetch_new_messages(mailbox_id="default")
                if messages:
                    logger.info("Inbound poller received %d new messages from provider", len(messages))

                    processed_ids = []
                    for inbound in messages:
                        msg_id = str(ULID())

                        # Resolve thread membership
                        thread_id = await self._resolve_thread(inbound, msg_id)

                        doc = MessageDoc(
                            id=msg_id,
                            user_id=self.user_id,
                            thread_id=thread_id,
                            folder_id="inbox",
                            subject=inbound.subject,
                            preview=inbound.body_text[:200] if inbound.body_text else "",
                            body_html=inbound.body_html,
                            body_text=inbound.body_text,
                            sender=MailRecipient(email=inbound.from_address, name=inbound.from_name),
                            recipients=inbound.to,
                            cc=inbound.cc,
                            received_at=inbound.received_at or datetime.now(timezone.utc),
                            is_read=False,
                            mail_in_reply_to=inbound.raw_headers.get("In-Reply-To"),
                            mail_references=self._parse_references(inbound.raw_headers.get("References", "")),
                            attachments=[],
                        )
                        await doc.insert()

                        # Refresh thread aggregates
                        await self._refresh_thread_aggregates(thread_id, doc)

                        # Evaluate rules
                        await rules_facade.evaluate_rules(self.user_id, doc)
                        processed_ids.append(inbound.provider_message_id)

                    # Acknowledge (delete from provider)
                    if processed_ids:
                        await self.adapter.acknowledge(processed_ids)

                # Update status tracking
                self.last_poll_at = datetime.now(timezone.utc)
                self.last_poll_status = "ok"
                self.last_error = None
                self.messages_last_cycle = len(messages) if messages else 0

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in inbound poller loop: %s", e)
                self.last_poll_at = datetime.now(timezone.utc)
                self.last_poll_status = "error"
                self.last_error = str(e)
                self.messages_last_cycle = 0
            finally:
                self.is_polling = False

            # Wait for interval or immediate trigger
            if self._trigger_event:
                self._trigger_event.clear()
                try:
                    await asyncio.wait_for(self._trigger_event.wait(), timeout=self.interval)
                except asyncio.TimeoutError:
                    pass  # Normal timeout — proceed to next poll

    async def _resolve_thread(self, inbound: InboundMessage, new_msg_id: str) -> str:
        """Determine the thread_id for an inbound message.

        Resolution order:
        1. In-Reply-To / References headers — look up existing messages
           whose Message-ID matches.
        2. Normalized subject + overlapping participants — find a recent
           thread with the same (stripped) subject and at least one common
           participant.
        3. Create a new thread.
        """
        user_id = self.user_id

        # 1. Try In-Reply-To header
        in_reply_to = inbound.raw_headers.get("In-Reply-To", "").strip()
        if in_reply_to:
            # Message-IDs in headers look like <id@domain> — strip angle brackets
            clean_id = in_reply_to.strip("<>")
            existing = await MessageDoc.find_one(
                MessageDoc.user_id == user_id,
                {"adapter_meta.message_id_header": clean_id},
            )
            if existing:
                return existing.thread_id

        # 2. Try References header (walk backwards, most recent first)
        references_raw = inbound.raw_headers.get("References", "")
        for ref in reversed(self._parse_references(references_raw)):
            existing = await MessageDoc.find_one(
                MessageDoc.user_id == user_id,
                {"adapter_meta.message_id_header": ref},
            )
            if existing:
                return existing.thread_id

        # 3. Subject + participant matching
        normalized = _normalize_subject(inbound.subject)
        if normalized:
            inbound_participants = {inbound.from_address.lower()}
            for r in inbound.to:
                inbound_participants.add(r.email.lower())
            for r in inbound.cc:
                inbound_participants.add(r.email.lower())

            # Find threads with same normalized subject
            candidates = await ThreadDoc.find(
                ThreadDoc.user_id == user_id,
            ).sort([("last_message_at", -1)]).limit(50).to_list()

            for thread in candidates:
                if _normalize_subject(thread.subject) == normalized:
                    thread_participants = {e.lower() for e in thread.participant_emails}
                    if inbound_participants & thread_participants:
                        return thread.id

        # 4. No match — create new thread
        thread_id = new_msg_id
        return thread_id

    async def _refresh_thread_aggregates(self, thread_id: str, new_msg: MessageDoc) -> None:
        """Create or update thread aggregates after inserting a new message."""
        user_id = self.user_id
        thread = await ThreadDoc.find_one(ThreadDoc.id == thread_id, ThreadDoc.user_id == user_id)

        if thread:
            # Update existing thread
            messages = await MessageDoc.find(
                MessageDoc.user_id == user_id, MessageDoc.thread_id == thread_id,
            ).to_list()

            last = max(messages, key=lambda m: m.received_at or datetime.min.replace(tzinfo=timezone.utc))
            thread.subject = last.subject
            thread.folder_id = last.folder_id
            thread.last_message_at = last.received_at
            thread.unread_count = sum(1 for m in messages if not m.is_read)
            thread.total_count = len(messages)
            thread.has_attachments = any(m.has_attachments for m in messages)
            thread.is_flagged = any(m.is_flagged for m in messages)
            thread.participant_emails = list({m.sender.email for m in messages})
            thread.message_ids = [m.id for m in messages]
            await thread.save()
        else:
            # Create new thread
            await ThreadDoc(
                id=thread_id,
                user_id=user_id,
                subject=new_msg.subject,
                folder_id=new_msg.folder_id,
                participant_emails=[new_msg.sender.email],
                message_ids=[new_msg.id],
                last_message_at=new_msg.received_at,
                unread_count=1 if not new_msg.is_read else 0,
                total_count=1,
                has_attachments=new_msg.has_attachments,
                is_flagged=new_msg.is_flagged,
            ).insert()

    @staticmethod
    def _parse_references(raw: str) -> list[str]:
        """Parse RFC 2822 References header into a list of clean message IDs."""
        if not raw:
            return []
        # References are space-separated angle-bracket IDs: <id1@a> <id2@b>
        return [ref.strip("<>") for ref in raw.split() if ref.strip()]
