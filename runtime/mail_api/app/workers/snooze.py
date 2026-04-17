"""PSense Mail — Snooze wake-up worker.

Periodically moves messages from 'snoozed' to 'inbox' if their snoozed_until time has passed.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.domain.models import MessageDoc

logger = logging.getLogger(__name__)


class SnoozeWorker:
    """Worker that wakes up snoozed messages."""

    def __init__(self, interval: int = 60):
        self.interval = interval
        self._running = False
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Snooze wake-up worker started (interval=%ds)", self.interval)

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Snooze wake-up worker stopped")

    async def _process_loop(self) -> None:
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                
                # Find all messages in the 'snoozed' folder where snoozed_until is in the past
                woken = await MessageDoc.find(
                    MessageDoc.folder_id == "snoozed",
                    MessageDoc.snoozed_until <= now,
                ).to_list()
                
                if woken:
                    logger.info("Waking up %d snoozed messages", len(woken))
                    for msg in woken:
                        msg.folder_id = "inbox"
                        msg.snoozed_until = None
                        msg.updated_at = now
                        await msg.save()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in snooze wake-up loop: %s", e)
                
            await asyncio.sleep(self.interval)
