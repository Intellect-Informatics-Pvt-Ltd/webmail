"""PSense Mail — Inbound Poller Worker.

Polls the inbound adapter for new messages and processes them through RulesFacade.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from ulid import ULID

from app.adapters.protocols import InboundAdapter
from app.domain.models import MailRecipient, MessageDoc

logger = logging.getLogger(__name__)


class InboundPollerWorker:
    """Worker that periodically polls for inbound messages."""

    def __init__(self, adapter: InboundAdapter, cache_user_id: str, poll_interval: int = 15):
        self.adapter = adapter
        self.interval = poll_interval
        self._running = False
        self._task: asyncio.Task | None = None
        self.user_id = cache_user_id

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Inbound poller worker started (interval=%ds)", self.interval)

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Inbound poller worker stopped")

    async def _poll_loop(self) -> None:
        from app.services.rules_facade import RulesFacade
        
        rules_facade = RulesFacade()
        
        while self._running:
            try:
                # Fetch new messages
                messages = await self.adapter.fetch_new_messages(mailbox_id="default")
                if messages:
                    logger.info("Inbound poller received %d new messages from provider", len(messages))
                    
                    processed_ids = []
                    for inbound in messages:
                        # Convert to MessageDoc
                        msg_id = str(ULID())
                        doc = MessageDoc(
                            id=msg_id,
                            user_id=self.user_id,
                            thread_id=msg_id,  # Simplified threading for now
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
                            attachments=[]  # Simplified attachment mapping for now
                        )
                        await doc.insert()
                        
                        # Evaluate rules
                        await rules_facade.evaluate_rules(self.user_id, doc)
                        processed_ids.append(inbound.provider_message_id)
                        
                    # Acknowledge (delete from MailPit)
                    if processed_ids:
                        await self.adapter.acknowledge(processed_ids)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in inbound poller loop: %s", e)
                
            await asyncio.sleep(self.interval)
