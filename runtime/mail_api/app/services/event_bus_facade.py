"""PSense Mail — Event Bus facade for webhook delivery.

Publishes events to registered webhook subscribers with HMAC-SHA256
signature verification. Failed deliveries are retried with exponential
backoff before being sent to the dead-letter queue.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.domain.models import DeadLetterDoc, WebhookSubscriptionDoc

logger = logging.getLogger(__name__)

# Retry delays in seconds: 30s, 300s, 3000s
_RETRY_DELAYS = [30, 300, 3000]


class EventBusFacade:
    """Delivers webhook event payloads to registered subscriber URLs."""

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        tenant_id: str,
        account_id: str = "",
    ) -> None:
        """Publish an event to all matching subscribers."""
        subs = await WebhookSubscriptionDoc.find(
            WebhookSubscriptionDoc.tenant_id == tenant_id,
            WebhookSubscriptionDoc.active == True,  # noqa: E712
            {"events": event_type},
        ).to_list()

        for sub in subs:
            try:
                await self._deliver(sub, event_type, payload)
            except Exception as exc:
                logger.warning(
                    "Webhook delivery failed for sub=%s event=%s: %s",
                    sub.id, event_type, exc,
                )
                # Enqueue to DLQ after exhausting retries
                await self._enqueue_dlq(sub, event_type, payload, str(exc), tenant_id, account_id)

    async def _deliver(
        self,
        sub: WebhookSubscriptionDoc,
        event_type: str,
        payload: dict[str, Any],
    ) -> int:
        """Deliver a single webhook — returns HTTP status code."""
        body = json.dumps({
            "event": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        signature = hmac.new(
            sub.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-PSense-Signature": f"sha256={signature}",
        }

        async with httpx.AsyncClient(timeout=10) as client:
            for attempt in range(len(_RETRY_DELAYS) + 1):
                try:
                    resp = await client.post(sub.url, content=body, headers=headers)
                    if 200 <= resp.status_code < 300:
                        # Update last_delivered_at
                        sub.last_delivered_at = datetime.now(timezone.utc)
                        sub.failure_count = 0
                        await sub.save()
                        return resp.status_code
                    # Non-2xx — retry
                    if attempt < len(_RETRY_DELAYS):
                        import asyncio
                        await asyncio.sleep(_RETRY_DELAYS[attempt])
                    else:
                        raise RuntimeError(f"Webhook returned {resp.status_code}")
                except httpx.HTTPError as exc:
                    if attempt < len(_RETRY_DELAYS):
                        import asyncio
                        await asyncio.sleep(_RETRY_DELAYS[attempt])
                    else:
                        raise RuntimeError(f"Webhook delivery failed: {exc}") from exc

        return 0  # unreachable

    async def _enqueue_dlq(
        self,
        sub: WebhookSubscriptionDoc,
        event_type: str,
        payload: dict[str, Any],
        error: str,
        tenant_id: str,
        account_id: str,
    ) -> None:
        """Write a dead-letter entry for failed webhook delivery."""
        sub.failure_count += 1
        await sub.save()

        await DeadLetterDoc(
            tenant_id=tenant_id,
            account_id=account_id,
            queue="webhook_delivery",
            payload={
                "subscription_id": sub.id,
                "event_type": event_type,
                "event_payload": payload,
                "url": sub.url,
            },
            error=error,
            retry_count=len(_RETRY_DELAYS) + 1,
            max_retries=len(_RETRY_DELAYS) + 1,
            last_attempt_at=datetime.now(timezone.utc),
        ).insert()

        logger.error(
            "Webhook delivery exhausted retries: sub=%s event=%s url=%s",
            sub.id, event_type, sub.url,
        )

    # ── Test ping ─────────────────────────────────────────────────────

    async def test_ping(self, subscription_id: str) -> dict[str, Any]:
        """Send a test ping to a webhook subscription."""
        sub = await WebhookSubscriptionDoc.find_one(
            WebhookSubscriptionDoc.id == subscription_id,
        )
        if not sub:
            return {"delivered": False, "error": "Subscription not found"}

        try:
            status = await self._deliver(sub, "ping", {})
            return {"delivered": True, "status_code": status}
        except Exception as exc:
            return {"delivered": False, "error": str(exc)}
