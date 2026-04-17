"""PSense Mail — Retry Worker.

Polls for failed-retryable delivery log entries and retries sending
with exponential backoff.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.domain.enums import DeliveryState
from app.domain.models import DeliveryLogDoc, DraftDoc

logger = logging.getLogger(__name__)


class RetryWorker:
    """Worker that automatically retries failed sends with exponential backoff."""

    def __init__(
        self,
        transport=None,
        interval: int = 60,
        max_attempts: int = 3,
        backoff_base_sec: int = 60,
        default_from_address: str = "noreply@psense.local",
    ):
        self._transport = transport
        self.interval = interval
        self._max_attempts = max_attempts
        self._backoff_base_sec = backoff_base_sec
        self._default_from_address = default_from_address
        self._running = False
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info(
            "Retry worker started (interval=%ds, max_attempts=%d, backoff=%ds)",
            self.interval, self._max_attempts, self._backoff_base_sec,
        )

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Retry worker stopped")

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

                # Find drafts in failed_retryable state
                failed_drafts = await DraftDoc.find(
                    DraftDoc.delivery_state == DeliveryState.FAILED_RETRYABLE,
                ).to_list()

                for draft in failed_drafts:
                    try:
                        # Count previous attempts from delivery log
                        attempt_count = await DeliveryLogDoc.find(
                            DeliveryLogDoc.draft_id == draft.id,
                            DeliveryLogDoc.state == DeliveryState.FAILED_RETRYABLE,
                        ).count()

                        if attempt_count >= self._max_attempts:
                            # Max retries exceeded — mark as permanent failure
                            draft.delivery_state = DeliveryState.FAILED_PERMANENT
                            await draft.save()
                            logger.warning(
                                "Draft %s exceeded max retries (%d), marked as permanent failure",
                                draft.id, self._max_attempts,
                            )
                            continue

                        # Exponential backoff: base * 2^attempt_count
                        backoff_seconds = self._backoff_base_sec * (2 ** attempt_count)
                        last_log = await DeliveryLogDoc.find(
                            DeliveryLogDoc.draft_id == draft.id,
                        ).sort([("timestamp", -1)]).first_or_none()

                        if last_log and last_log.timestamp:
                            next_retry_at = last_log.timestamp + timedelta(seconds=backoff_seconds)
                            if now < next_retry_at:
                                continue  # Not yet time to retry

                        # Attempt retry
                        logger.info(
                            "Retrying draft %s (attempt %d/%d)",
                            draft.id, attempt_count + 1, self._max_attempts,
                        )
                        receipt = await facade.send_draft(
                            user_id=draft.user_id,
                            draft_id=draft.id,
                            request=SendDraftRequest(),
                        )
                        logger.info(
                            "Retry send result: draft=%s message=%s state=%s",
                            draft.id, receipt.message_id, receipt.state,
                        )

                    except Exception as e:
                        logger.error("Retry failed for draft %s: %s", draft.id, e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in retry worker loop: %s", e)

            await asyncio.sleep(self.interval)
