"""Reference façade skeleton for an enterprise mail backend.

This file is intentionally implementation-light and designed for handoff to
a developer or Cursor. It defines the contracts that the FastAPI layer should
depend on.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Protocol
from pydantic import BaseModel, Field


class DeliveryState(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_PERMANENT = "failed_permanent"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class FolderKind(str, Enum):
    INBOX = "inbox"
    FOCUSED = "focused"
    OTHER = "other"
    DRAFTS = "drafts"
    SENT = "sent"
    ARCHIVE = "archive"
    SNOOZED = "snoozed"
    FLAGGED = "flagged"
    DELETED = "deleted"
    JUNK = "junk"
    CUSTOM = "custom"


class MailDomainError(Exception):
    """Base domain error."""


class NotFoundError(MailDomainError): ...
class ValidationError(MailDomainError): ...
class ConflictError(MailDomainError): ...
class ConcurrencyError(MailDomainError): ...
class PolicyDeniedError(MailDomainError): ...
class ProviderUnavailableError(MailDomainError): ...
class RateLimitedError(MailDomainError): ...
class RetryableDeliveryError(MailDomainError): ...
class PermanentDeliveryError(MailDomainError): ...


class MailRecipient(BaseModel):
    email: str
    display_name: str | None = None


class MailAttachment(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    inline: bool = False
    content_id: str | None = None
    checksum: str | None = None
    adapter_meta: dict[str, Any] = Field(default_factory=dict)


class MailMessage(BaseModel):
    id: str
    thread_id: str
    folder_id: str
    subject: str
    preview: str
    body_html: str | None = None
    body_text: str | None = None
    sender: MailRecipient
    to: list[MailRecipient] = Field(default_factory=list)
    cc: list[MailRecipient] = Field(default_factory=list)
    bcc: list[MailRecipient] = Field(default_factory=list)
    received_at: datetime | None = None
    sent_at: datetime | None = None
    is_read: bool = False
    is_flagged: bool = False
    is_pinned: bool = False
    has_mentions: bool = False
    categories: list[str] = Field(default_factory=list)
    attachments: list[MailAttachment] = Field(default_factory=list)
    delivery_state: DeliveryState = DeliveryState.DRAFT
    version: str | None = None
    adapter_meta: dict[str, Any] = Field(default_factory=dict)


class MailThread(BaseModel):
    id: str
    mailbox_id: str
    folder_id: str
    subject: str
    last_message_at: datetime | None = None
    unread_count: int = 0
    total_count: int = 0
    messages: list[MailMessage] = Field(default_factory=list)


class MailFolder(BaseModel):
    id: str
    mailbox_id: str
    display_name: str
    kind: FolderKind
    unread_count: int = 0
    total_count: int = 0
    sort_order: int = 0


class ComposeDraft(BaseModel):
    id: str
    mailbox_id: str
    subject: str = ""
    body_html: str | None = None
    body_text: str | None = None
    to: list[MailRecipient] = Field(default_factory=list)
    cc: list[MailRecipient] = Field(default_factory=list)
    bcc: list[MailRecipient] = Field(default_factory=list)
    attachments: list[MailAttachment] = Field(default_factory=list)
    delivery_state: DeliveryState = DeliveryState.DRAFT
    version: str | None = None
    updated_at: datetime | None = None


class SearchRequest(BaseModel):
    mailbox_id: str
    query: str | None = None
    folder_id: str | None = None
    sender: str | None = None
    recipient: str | None = None
    subject: str | None = None
    unread: bool | None = None
    flagged: bool | None = None
    has_attachments: bool | None = None
    categories: list[str] = Field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    cursor: str | None = None
    limit: int = 50


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


class DraftCreate(BaseModel):
    mailbox_id: str
    subject: str = ""
    body_html: str | None = None
    body_text: str | None = None
    to: list[MailRecipient] = Field(default_factory=list)
    cc: list[MailRecipient] = Field(default_factory=list)
    bcc: list[MailRecipient] = Field(default_factory=list)


class DraftPatch(BaseModel):
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    to: list[MailRecipient] | None = None
    cc: list[MailRecipient] | None = None
    bcc: list[MailRecipient] | None = None
    attachment_ids: list[str] | None = None


class SendRequest(BaseModel):
    idempotency_key: str | None = None
    expected_version: str | None = None
    schedule_at: datetime | None = None


class DeliveryReceipt(BaseModel):
    message_id: str
    draft_id: str | None = None
    state: DeliveryState
    transport_message_id: str | None = None
    accepted_at: datetime | None = None
    diagnostic_code: str | None = None
    correlation_id: str | None = None


class MessageActionRequest(BaseModel):
    action: Literal[
        "archive", "delete", "restore", "move",
        "mark_read", "mark_unread", "flag", "unflag",
        "pin", "unpin", "snooze", "unsnooze",
        "categorize", "uncategorize"
    ]
    destination_folder_id: str | None = None
    category_ids: list[str] = Field(default_factory=list)
    snooze_until: datetime | None = None
    reason: str | None = None


class BulkActionResult(BaseModel):
    succeeded_ids: list[str] = Field(default_factory=list)
    failed: dict[str, str] = Field(default_factory=dict)
    correlation_id: str | None = None


class ThreadQuery(BaseModel):
    cursor: str | None = None
    limit: int = 50
    unread_only: bool = False


class ThreadPage(BaseModel):
    items: list[MailThread] = Field(default_factory=list)
    next_cursor: str | None = None


class AttachmentInitRequest(BaseModel):
    mailbox_id: str
    filename: str
    content_type: str
    size_bytes: int


class AttachmentUploadSession(BaseModel):
    attachment_id: str
    upload_url: str | None = None
    expires_at: datetime | None = None


class HealthReport(BaseModel):
    status: Literal["ok", "degraded", "down"]
    storage: str
    transport: str
    search: str
    timestamp: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class MailFacade(Protocol):
    async def list_folders(self, mailbox_id: str) -> list[MailFolder]: ...
    async def list_threads(self, mailbox_id: str, folder_id: str, query: ThreadQuery) -> ThreadPage: ...
    async def get_thread(self, thread_id: str, include_bodies: bool = True) -> MailThread: ...
    async def get_message(self, message_id: str) -> MailMessage: ...
    async def apply_message_action(
        self,
        mailbox_id: str,
        message_ids: list[str],
        request: MessageActionRequest,
        *,
        idempotency_key: str | None = None,
    ) -> BulkActionResult: ...


class ComposeFacade(Protocol):
    async def create_draft(
        self,
        payload: DraftCreate,
        *,
        idempotency_key: str | None = None,
    ) -> ComposeDraft: ...

    async def update_draft(
        self,
        draft_id: str,
        patch: DraftPatch,
        *,
        expected_version: str | None = None,
        idempotency_key: str | None = None,
    ) -> ComposeDraft: ...

    async def send_draft(self, draft_id: str, request: SendRequest) -> DeliveryReceipt: ...
    async def retry_send(self, message_id: str, *, idempotency_key: str | None = None) -> DeliveryReceipt: ...


class SearchFacade(Protocol):
    async def search_messages(self, request: SearchRequest) -> SearchResponse: ...


class AttachmentFacade(Protocol):
    async def upload_attachment_init(self, request: AttachmentInitRequest) -> AttachmentUploadSession: ...
    async def finalize_attachment(self, attachment_id: str) -> MailAttachment: ...
    async def get_attachment(self, attachment_id: str) -> MailAttachment: ...


class AdminFacade(Protocol):
    async def get_system_health(self) -> HealthReport: ...
    async def seed_demo_mailbox(self, mailbox_id: str, *, scenario: str = "default") -> dict[str, Any]: ...
    async def replay_failed_sends(self, mailbox_id: str | None = None) -> dict[str, Any]: ...
