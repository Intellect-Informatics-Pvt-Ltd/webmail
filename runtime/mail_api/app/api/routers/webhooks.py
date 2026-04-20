"""PSense Mail — Webhooks router.

CRUD for webhook subscriptions + test ping endpoint.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.dependencies import get_current_user
from app.domain.models import WebhookSubscriptionDoc
from app.middleware.auth import AuthenticatedUser

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


# ── Request models ────────────────────────────────────────────────────────

class CreateWebhookRequest(BaseModel):
    url: str
    events: list[str] = Field(default_factory=list)
    secret: str = ""

    @field_validator("url")
    @classmethod
    def validate_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("Webhook URL must use HTTPS scheme")
        return v


class UpdateWebhookRequest(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    secret: str | None = None
    active: bool | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/")
async def list_webhooks(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all webhook subscriptions for the tenant."""
    docs = await WebhookSubscriptionDoc.find(
        WebhookSubscriptionDoc.tenant_id == user.tenant_id,
    ).to_list()
    return {"items": [d.model_dump(mode="json") for d in docs]}


@router.post("/", status_code=201)
async def create_webhook(
    body: CreateWebhookRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new webhook subscription."""
    doc = WebhookSubscriptionDoc(
        tenant_id=user.tenant_id,
        url=body.url,
        events=body.events,
        secret=body.secret,
        active=True,
    )
    await doc.insert()
    return doc.model_dump(mode="json")


@router.patch("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    body: UpdateWebhookRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Update a webhook subscription."""
    doc = await WebhookSubscriptionDoc.find_one(
        WebhookSubscriptionDoc.id == webhook_id,
        WebhookSubscriptionDoc.tenant_id == user.tenant_id,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if body.url is not None:
        if not body.url.startswith("https://"):
            raise HTTPException(status_code=400, detail="URL must use HTTPS")
        doc.url = body.url
    if body.events is not None:
        doc.events = body.events
    if body.secret is not None:
        doc.secret = body.secret
    if body.active is not None:
        doc.active = body.active
    doc.updated_at = datetime.now(timezone.utc)
    await doc.save()
    return doc.model_dump(mode="json")


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Delete a webhook subscription."""
    doc = await WebhookSubscriptionDoc.find_one(
        WebhookSubscriptionDoc.id == webhook_id,
        WebhookSubscriptionDoc.tenant_id == user.tenant_id,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await doc.delete()


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Send a test ping event to the webhook URL."""
    from app.services.event_bus_facade import EventBusFacade
    facade = EventBusFacade()
    return await facade.test_ping(webhook_id)
