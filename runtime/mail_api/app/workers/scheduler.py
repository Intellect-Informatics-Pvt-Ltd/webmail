"""PSense Mail — Scheduled Send Worker.

Polls for drafts with a scheduled_for time in the past and triggers
their send via ComposeFacade.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.domain.enums import DeliveryState
from app.domain.models import DraftDoc

logger = logging.getLogger(__name__)


class ScheduledSendWorker:
    """Worker that sends drafts when their scheduled time arrives."""

    def __init__(self, transport=None, interval: int = 30, default_from_address: str = "noreply@psense.local"):
        self._transport = transport
        self.interval = interval
        self._default_from_address = default_from_address
        self._running = False
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("Scheduled send worker started (interval=%ds)", self.interval)

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Scheduled send worker stopped")

    async def _process_loop(self) -> None:
        from app.domain.requests import SendDraftRequest
        from app.services.compose_facade import ComposeFacade

        facade = ComposeFacade(
            transport=self._transport,
            default_from_address=self._default_from_address,
        )

        while self._running:
            try:
                now = datetime.now(timezone.utc)

                # Find drafts that are scheduled and due
                due_drafts = await DraftDoc.find(
                    DraftDoc.delivery_state == DeliveryState.SCHEDULED,
                    DraftDoc.scheduled_for <= now,
                ).to_list()

                if due_drafts:
                    logger.info("Scheduled send worker found %d due drafts", len(due_drafts))

                for draft in due_drafts:
                    try:
                        # Reset scheduled_for so send_draft doesn't re-schedule
                        draft.scheduled_for = None
                        draft.delivery_state = DeliveryState.QUEUED
                        await draft.save()

                        receipt = await facade.send_draft(
                            user_id=draft.user_id,
                            draft_id=draft.id,
                            request=SendDraftRequest(),
                        )
                        logger.info(
                            "Scheduled send completed: draft=%s message=%s state=%s",
                            draft.id, receipt.message_id, receipt.state,
                        )
                    except Exception as e:
                        logger.error("Scheduled send failed for draft %s: %s", draft.id, e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in scheduled send worker loop: %s", e)

            await asyncio.sleep(self.interval)
