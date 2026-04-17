"""PSense Mail — Request DTOs.

Inbound request payloads for the API. These are separate from domain models
so the API contract can evolve independently of the storage schema.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import (
    Importance,
    MessageAction,
    RuleActionType,
    RuleConditionField,
    RuleConditionOp,
)
from app.domain.models import MailRecipient, RuleAction, RuleCondition


# ── Messages ─────────────────────────────────────────────────────────────────


class MessageListQuery(BaseModel):
    """Query parameters for listing messages."""
    folder_id: str | None = None
    category_id: str | None = None
    is_read: bool | None = None
    is_flagged: bool | None = None
    is_focused: bool | None = None
    has_attachments: bool | None = None
    has_mentions: bool | None = None
    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    sort_by: str = "received_at"
    sort_order: str = "desc"  # "asc" | "desc"


class MessageActionRequest(BaseModel):
    """Request to apply an action to one or more messages."""
    message_ids: list[str]
    action: MessageAction
    destination_folder_id: str | None = None
    category_ids: list[str] = Field(default_factory=list)
    snooze_until: datetime | None = None
    reason: str | None = None
    idempotency_key: str | None = None
    expected_version: int | None = None  # optimistic concurrency check


# ── Drafts ───────────────────────────────────────────────────────────────────


class DraftCreateRequest(BaseModel):
    """Create a new compose draft."""
    subject: str = ""
    body_html: str | None = None
    body_text: str | None = None
    to: list[MailRecipient] = Field(default_factory=list)
    cc: list[MailRecipient] = Field(default_factory=list)
    bcc: list[MailRecipient] = Field(default_factory=list)
    in_reply_to_id: str | None = None
    scheduled_for: datetime | None = None


class DraftPatchRequest(BaseModel):
    """Partial update to an existing draft."""
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    to: list[MailRecipient] | None = None
    cc: list[MailRecipient] | None = None
    bcc: list[MailRecipient] | None = None
    scheduled_for: datetime | None = None
    signature_disabled: bool | None = None


class SendDraftRequest(BaseModel):
    """Send a draft."""
    idempotency_key: str | None = None
    expected_version: int | None = None
    schedule_at: datetime | None = None


# ── Folders ──────────────────────────────────────────────────────────────────


class FolderCreateRequest(BaseModel):
    name: str
    parent_id: str | None = None


class FolderRenameRequest(BaseModel):
    name: str


# ── Rules ────────────────────────────────────────────────────────────────────


class RuleCreateRequest(BaseModel):
    name: str
    enabled: bool = True
    conditions: list[RuleCondition]
    actions: list[RuleAction]


class RuleUpdateRequest(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    conditions: list[RuleCondition] | None = None
    actions: list[RuleAction] | None = None


# ── Templates ────────────────────────────────────────────────────────────────


class TemplateCreateRequest(BaseModel):
    name: str
    subject: str = ""
    body_html: str = ""


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    subject: str | None = None
    body_html: str | None = None


# ── Signatures ───────────────────────────────────────────────────────────────


class SignatureCreateRequest(BaseModel):
    name: str
    body_html: str = ""
    is_default: bool = False


class SignatureUpdateRequest(BaseModel):
    name: str | None = None
    body_html: str | None = None
    is_default: bool | None = None


# ── Categories ───────────────────────────────────────────────────────────────


class CategoryCreateRequest(BaseModel):
    name: str
    color: str


class CategoryUpdateRequest(BaseModel):
    name: str | None = None
    color: str | None = None


# ── Saved Searches ───────────────────────────────────────────────────────────


class SavedSearchCreateRequest(BaseModel):
    name: str
    query: str = ""
    filters: dict[str, Any] = Field(default_factory=dict)


# ── Preferences ──────────────────────────────────────────────────────────────


class PreferencesPatchRequest(BaseModel):
    """Partial update to user preferences. All fields optional."""
    density: str | None = None
    reading_pane: str | None = None
    conversation_view: bool | None = None
    focused_inbox: bool | None = None
    default_sort: str | None = None
    preview_lines: int | None = None
    theme: str | None = None
    default_reply: str | None = None
    notifications: dict[str, Any] | None = None
    out_of_office: dict[str, Any] | None = None
    shortcuts_enabled: bool | None = None


# ── Search ───────────────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    """Structured search request."""
    query: str | None = None
    folder_id: str | None = None
    sender: str | None = None
    recipient: str | None = None
    subject: str | None = None
    is_read: bool | None = None
    is_flagged: bool | None = None
    has_attachments: bool | None = None
    categories: list[str] = Field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


# ── Attachments ──────────────────────────────────────────────────────────────


class AttachmentInitRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int


# ── Admin ────────────────────────────────────────────────────────────────────


class SeedRequest(BaseModel):
    scenario: str = "default"
