"""PSense Mail — Response DTOs.

Outbound response payloads for the API. These wrap domain models with
pagination cursors, action results, and health information.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from app.domain.enums import DeliveryState
from app.domain.models import MailRecipient


# ── Pagination ───────────────────────────────────────────────────────────────

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    """Generic cursor-paginated response."""
    items: list[T] = Field(default_factory=list)
    next_cursor: str | None = None
    total_estimate: int | None = None


# ── Message responses ────────────────────────────────────────────────────────


class MessageSummary(BaseModel):
    """Lightweight message for list views (body omitted)."""
    id: str
    thread_id: str
    folder_id: str
    subject: str
    preview: str
    sender: MailRecipient
    recipients: list[MailRecipient] = Field(default_factory=list)
    received_at: datetime | None = None
    is_read: bool = False
    is_flagged: bool = False
    is_pinned: bool = False
    has_attachments: bool = False
    has_mentions: bool = False
    importance: str = "normal"
    categories: list[str] = Field(default_factory=list)
    is_draft: bool = False
    is_focused: bool = False
    snoozed_until: datetime | None = None
    scheduled_for: datetime | None = None
    trust_verified: bool = False


class AttachmentSummary(BaseModel):
    id: str
    name: str
    size: int
    mime: str


class MessageDetail(MessageSummary):
    """Full message with body and attachment details."""
    body_html: str | None = None
    body_text: str | None = None
    cc: list[MailRecipient] = Field(default_factory=list)
    bcc: list[MailRecipient] = Field(default_factory=list)
    attachments: list[AttachmentSummary] = Field(default_factory=list)
    in_reply_to_id: str | None = None
    delivery_state: DeliveryState = DeliveryState.SENT
    version: int = 1


class ThreadDetail(BaseModel):
    """Thread with its messages."""
    id: str
    subject: str
    folder_id: str
    participant_emails: list[str] = Field(default_factory=list)
    last_message_at: datetime | None = None
    unread_count: int = 0
    total_count: int = 0
    has_attachments: bool = False
    is_flagged: bool = False
    messages: list[MessageDetail] = Field(default_factory=list)


# ── Bulk action result ───────────────────────────────────────────────────────


class BulkActionResult(BaseModel):
    succeeded_ids: list[str] = Field(default_factory=list)
    failed: dict[str, str] = Field(default_factory=dict)
    correlation_id: str | None = None


# ── Folder responses ─────────────────────────────────────────────────────────


class FolderResponse(BaseModel):
    id: str
    name: str
    kind: str
    system: bool = False
    parent_id: str | None = None
    sort_order: int = 0
    icon: str | None = None
    unread_count: int = 0
    total_count: int = 0


class FolderCountsResponse(BaseModel):
    counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    # e.g., {"inbox": {"unread": 5, "total": 42}, ...}


# ── Draft responses ──────────────────────────────────────────────────────────


class DraftResponse(BaseModel):
    id: str
    subject: str
    body_html: str | None = None
    to: list[MailRecipient] = Field(default_factory=list)
    cc: list[MailRecipient] = Field(default_factory=list)
    bcc: list[MailRecipient] = Field(default_factory=list)
    attachments: list[AttachmentSummary] = Field(default_factory=list)
    delivery_state: DeliveryState = DeliveryState.DRAFT
    scheduled_for: datetime | None = None
    in_reply_to_id: str | None = None
    signature_disabled: bool = False
    version: int = 1
    last_saved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DeliveryReceipt(BaseModel):
    message_id: str
    draft_id: str | None = None
    state: DeliveryState
    transport_message_id: str | None = None
    accepted_at: datetime | None = None
    diagnostic_code: str | None = None
    correlation_id: str | None = None


# ── Search responses ─────────────────────────────────────────────────────────


class SearchHit(BaseModel):
    message_id: str
    thread_id: str
    subject: str
    preview: str
    sender: MailRecipient
    matched_fields: list[str] = Field(default_factory=list)
    received_at: datetime | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHit] = Field(default_factory=list)
    next_cursor: str | None = None
    total_estimate: int | None = None
    facets: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


# ── Health ───────────────────────────────────────────────────────────────────


class AdapterHealth(BaseModel):
    name: str
    status: Literal["ok", "degraded", "down"]
    latency_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class HealthReport(BaseModel):
    status: Literal["ok", "degraded", "down"]
    adapters: list[AdapterHealth] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Generic ──────────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Standard error envelope."""
    error: str
    code: str
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class SuccessResponse(BaseModel):
    """Simple success acknowledgement."""
    ok: bool = True
    message: str = ""
