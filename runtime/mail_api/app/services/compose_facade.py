"""PSense Mail — ComposeFacade service.

Draft lifecycle: create, update, save, discard, send, retry.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ulid import ULID

from app.domain.enums import DeliveryState
from app.domain.errors import ConcurrencyError, NotFoundError, ValidationError
from app.domain.models import (
    DeliveryLogDoc,
    DraftDoc,
    IdempotencyRecord,
    MailRecipient,
    MessageDoc,
    ThreadDoc,
)
from app.domain.requests import DraftCreateRequest, DraftPatchRequest, SendDraftRequest
from app.domain.responses import AttachmentSummary, DeliveryReceipt, DraftResponse

logger = logging.getLogger(__name__)


def _draft_to_response(d: DraftDoc) -> DraftResponse:
    return DraftResponse(
        id=d.id, subject=d.subject, body_html=d.body_html,
        to=d.to, cc=d.cc, bcc=d.bcc,
        attachments=[AttachmentSummary(id=a.id, name=a.name, size=a.size, mime=a.mime) for a in d.attachments],
        delivery_state=d.delivery_state,
        scheduled_for=d.scheduled_for,
        in_reply_to_id=d.in_reply_to_id,
        signature_disabled=d.signature_disabled,
        version=d.version,
        last_saved_at=d.last_saved_at,
        created_at=d.created_at, updated_at=d.updated_at,
    )


class ComposeFacade:
    """Compose/draft lifecycle facade."""

    def __init__(self, transport=None, default_from_address: str = "noreply@psense.local"):
        self._transport = transport
        self._default_from_address = default_from_address

    async def list_drafts(self, user_id: str, tenant_id: str = "default", account_id: str = "") -> list[DraftResponse]:
        """List all drafts for a user."""
        docs = await DraftDoc.find(DraftDoc.user_id == user_id).sort([("updated_at", -1)]).to_list()
        return [_draft_to_response(d) for d in docs]

    async def create_draft(self, user_id: str, payload: DraftCreateRequest, tenant_id: str = "default", account_id: str = "") -> DraftResponse:
        """Create a new draft."""
        draft = DraftDoc(
            user_id=user_id,
            tenant_id=tenant_id,
            account_id=account_id or user_id,
            subject=payload.subject,
            body_html=payload.body_html,
            body_text=payload.body_text,
            to=payload.to,
            cc=payload.cc,
            bcc=payload.bcc,
            in_reply_to_id=payload.in_reply_to_id,
            scheduled_for=payload.scheduled_for,
        )
        await draft.insert()
        logger.info("Created draft %s for user %s", draft.id, user_id)
        return _draft_to_response(draft)

    async def update_draft(
        self, user_id: str, draft_id: str, patch: DraftPatchRequest,
        expected_version: int | None = None,
    ) -> DraftResponse:
        """Partially update a draft."""
        draft = await DraftDoc.find_one(DraftDoc.id == draft_id, DraftDoc.user_id == user_id)
        if not draft:
            raise NotFoundError("Draft", draft_id)

        if expected_version is not None and draft.version != expected_version:
            raise ConcurrencyError("Draft", draft_id, str(expected_version))

        patch_data = patch.model_dump(exclude_none=True)
        for key, val in patch_data.items():
            setattr(draft, key, val)

        draft.updated_at = datetime.now(timezone.utc)
        draft.version += 1
        await draft.save()
        return _draft_to_response(draft)

    async def save_draft(self, user_id: str, draft_id: str) -> DraftResponse:
        """Explicitly save a draft (update last_saved_at)."""
        draft = await DraftDoc.find_one(DraftDoc.id == draft_id, DraftDoc.user_id == user_id)
        if not draft:
            raise NotFoundError("Draft", draft_id)

        draft.last_saved_at = datetime.now(timezone.utc)
        draft.updated_at = datetime.now(timezone.utc)
        await draft.save()
        return _draft_to_response(draft)

    async def discard_draft(self, user_id: str, draft_id: str) -> None:
        """Delete a draft permanently."""
        draft = await DraftDoc.find_one(DraftDoc.id == draft_id, DraftDoc.user_id == user_id)
        if not draft:
            raise NotFoundError("Draft", draft_id)
        await draft.delete()
        logger.info("Discarded draft %s", draft_id)

    async def send_draft(
        self, user_id: str, draft_id: str, request: SendDraftRequest,
        user_email: str | None = None, user_name: str | None = None,
        tenant_id: str = "default", account_id: str = "",
    ) -> DeliveryReceipt:
        """Send a draft via the configured transport adapter."""
        # Idempotency check
        if request.idempotency_key:
            existing = await IdempotencyRecord.find_one(
                IdempotencyRecord.id == request.idempotency_key,
                IdempotencyRecord.user_id == user_id,
            )
            if existing and existing.response_json:
                import json
                cached = json.loads(existing.response_json)
                return DeliveryReceipt(**cached)

        draft = await DraftDoc.find_one(DraftDoc.id == draft_id, DraftDoc.user_id == user_id)
        if not draft:
            raise NotFoundError("Draft", draft_id)

        if request.expected_version is not None and draft.version != request.expected_version:
            raise ConcurrencyError("Draft", draft_id, str(request.expected_version))

        # Validate
        if not draft.to:
            raise ValidationError("At least one recipient required", field="to")

        # Schedule send
        if request.schedule_at:
            draft.scheduled_for = request.schedule_at
            draft.delivery_state = DeliveryState.SCHEDULED
            draft.updated_at = datetime.now(timezone.utc)
            await draft.save()
            return DeliveryReceipt(
                message_id=draft.id, draft_id=draft_id,
                state=DeliveryState.SCHEDULED,
            )

        # Attempt send
        draft.delivery_state = DeliveryState.SENDING
        await draft.save()

        receipt = DeliveryReceipt(
            message_id=str(ULID()), draft_id=draft_id,
            state=DeliveryState.SENT,
            accepted_at=datetime.now(timezone.utc),
            correlation_id=request.idempotency_key,
        )

        try:
            if self._transport:
                from app.adapters.protocols import OutboundMessage

                sender_email = user_email or self._default_from_address
                sender_name = user_name or ""
                outbound = OutboundMessage(
                    message_id=receipt.message_id,
                    from_address=sender_email, from_name=sender_name,
                    to=draft.to, cc=draft.cc, bcc=draft.bcc,
                    subject=draft.subject,
                    body_html=draft.body_html, body_text=draft.body_text,
                )
                transport_receipt = await self._transport.send(outbound)
                receipt.transport_message_id = transport_receipt.transport_message_id

            # Create the sent message
            sender_email = user_email or self._default_from_address
            sender_name = user_name or ""
            sent_msg = MessageDoc(
                id=receipt.message_id, user_id=user_id,
                thread_id=draft.in_reply_to_id or str(ULID()),
                folder_id="sent", subject=draft.subject,
                preview=draft.body_text[:200] if draft.body_text else "",
                body_html=draft.body_html, body_text=draft.body_text,
                sender=MailRecipient(email=sender_email, name=sender_name),
                recipients=draft.to, cc=draft.cc, bcc=draft.bcc,
                received_at=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc),
                is_read=True,
                delivery_state=DeliveryState.SENT,
                attachments=draft.attachments,
            )
            await sent_msg.insert()

            # Delete the draft
            await draft.delete()

            # Log delivery
            await DeliveryLogDoc(
                message_id=receipt.message_id, draft_id=draft_id,
                state=DeliveryState.SENT,
                transport_message_id=receipt.transport_message_id,
                correlation_id=request.idempotency_key,
            ).insert()

            logger.info("Sent message %s (draft %s)", receipt.message_id, draft_id)

            # Store idempotency record
            if request.idempotency_key:
                import json
                await IdempotencyRecord(
                    id=request.idempotency_key,
                    user_id=user_id,
                    operation="send_draft",
                    response_json=json.dumps(receipt.model_dump(), default=str),
                ).insert()

        except Exception as e:
            draft.delivery_state = DeliveryState.FAILED_RETRYABLE
            await draft.save()

            receipt.state = DeliveryState.FAILED_RETRYABLE
            receipt.diagnostic_code = str(e)

            await DeliveryLogDoc(
                message_id=receipt.message_id, draft_id=draft_id,
                state=DeliveryState.FAILED_RETRYABLE,
                diagnostic_code=str(e),
                correlation_id=request.idempotency_key,
            ).insert()

            logger.error("Send failed for draft %s: %s", draft_id, e)

        return receipt

    async def retry_send(self, user_id: str, message_id: str) -> DeliveryReceipt:
        """Retry a failed send."""
        # Find the draft that failed
        draft = await DraftDoc.find_one(
            DraftDoc.user_id == user_id,
            DraftDoc.delivery_state == DeliveryState.FAILED_RETRYABLE,
        )
        if not draft:
            raise NotFoundError("Draft (failed)", message_id)

        return await self.send_draft(user_id, draft.id, SendDraftRequest())
