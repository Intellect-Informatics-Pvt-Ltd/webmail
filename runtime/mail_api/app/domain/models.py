"""PSense Mail — Domain models (Beanie Documents for MongoDB).

Every model maps 1:1 to a MongoDB collection. Field names use snake_case in
Python but serialize to camelCase for the REST API via Pydantic aliases where
the frontend expects it.

These models match the TypeScript types in webmail_ui/src/types/mail.ts with
full field parity — plus server-side additions (version, delivery_state,
adapter_meta, timestamps).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from beanie import Document, Indexed
from pydantic import BaseModel, Field
from ulid import ULID

from app.domain.enums import (
    DefaultReply,
    DefaultSort,
    Density,
    DeliveryState,
    FolderKind,
    Importance,
    ReadingPanePlacement,
    RuleActionType,
    RuleConditionField,
    RuleConditionOp,
    Theme,
)


def _new_id() -> str:
    """Generate a sortable ULID string."""
    return str(ULID())


# ── Embedded sub-documents (not standalone collections) ──────────────────────


class MailRecipient(BaseModel):
    """Email address + display name."""
    email: str
    name: str = ""
    avatar_color: str | None = None


class MailAttachmentMeta(BaseModel):
    """Attachment metadata stored on the message document."""
    id: str = Field(default_factory=_new_id)
    name: str
    size: int  # bytes
    mime: str
    inline: bool = False
    content_id: str | None = None
    checksum: str | None = None
    storage_path: str | None = None  # filled after upload
    adapter_meta: dict[str, Any] = Field(default_factory=dict)


class RuleCondition(BaseModel):
    """Single condition within a mail rule."""
    field: RuleConditionField
    op: RuleConditionOp
    value: str | bool | int  # type depends on field


class RuleAction(BaseModel):
    """Single action within a mail rule."""
    type: RuleActionType
    folder_id: str | None = None  # for 'move'
    category_id: str | None = None  # for 'categorize'


class NotificationPrefs(BaseModel):
    desktop: bool = True
    sound: bool = False
    only_focused: bool = True


class OutOfOfficePrefs(BaseModel):
    enabled: bool = False
    message: str = ""


# ── Top-level Beanie Documents (MongoDB collections) ────────────────────────


class UserDoc(Document):
    """Represents a user profile (populated from KeyCloak on first login)."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    email: str
    display_name: str = ""
    avatar_url: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = ["email"]


class FolderDoc(Document):
    """Mail folder — system (inbox, sent, …) or user-created custom."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    user_id: str
    name: str
    kind: FolderKind = FolderKind.CUSTOM
    system: bool = False
    parent_id: str | None = None
    sort_order: int = 0
    icon: str | None = None

    class Settings:
        name = "folders"
        indexes = [
            [("user_id", 1), ("kind", 1)],
        ]


class CategoryDoc(Document):
    """User-defined message category (e.g., Sales, Internal, Newsletter)."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    user_id: str
    name: str
    color: str  # semantic color token

    class Settings:
        name = "categories"
        indexes = ["user_id"]


class MessageDoc(Document):
    """A single email message within a thread."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    user_id: str
    thread_id: str
    folder_id: str
    subject: str
    preview: str = ""
    body_html: str | None = None
    body_text: str | None = None
    sender: MailRecipient
    recipients: list[MailRecipient] = Field(default_factory=list)
    cc: list[MailRecipient] = Field(default_factory=list)
    bcc: list[MailRecipient] = Field(default_factory=list)
    received_at: datetime | None = None
    sent_at: datetime | None = None
    is_read: bool = False
    is_flagged: bool = False
    is_pinned: bool = False
    has_attachments: bool = False
    has_mentions: bool = False
    importance: Importance = Importance.NORMAL
    categories: list[str] = Field(default_factory=list)
    attachments: list[MailAttachmentMeta] = Field(default_factory=list)
    snoozed_until: datetime | None = None
    scheduled_for: datetime | None = None
    is_draft: bool = False
    is_focused: bool = False
    trust_verified: bool = False
    in_reply_to_id: str | None = None
    delivery_state: DeliveryState = DeliveryState.SENT
    version: int = 1
    adapter_meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "messages"
        indexes = [
            [("user_id", 1), ("folder_id", 1), ("received_at", -1)],
            [("user_id", 1), ("thread_id", 1)],
            [("user_id", 1), ("is_read", 1)],
            [("user_id", 1), ("is_flagged", 1)],
            [("user_id", 1), ("is_pinned", 1)],
            [("user_id", 1), ("categories", 1)],
        ]


class ThreadDoc(Document):
    """Aggregated thread metadata."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    user_id: str
    subject: str
    folder_id: str
    participant_emails: list[str] = Field(default_factory=list)
    message_ids: list[str] = Field(default_factory=list)
    last_message_at: datetime | None = None
    unread_count: int = 0
    total_count: int = 0
    has_attachments: bool = False
    is_flagged: bool = False

    class Settings:
        name = "threads"
        indexes = [
            [("user_id", 1), ("folder_id", 1), ("last_message_at", -1)],
        ]


class DraftDoc(Document):
    """Compose draft — separate collection for clear lifecycle management."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    user_id: str
    subject: str = ""
    body_html: str | None = None
    body_text: str | None = None
    to: list[MailRecipient] = Field(default_factory=list)
    cc: list[MailRecipient] = Field(default_factory=list)
    bcc: list[MailRecipient] = Field(default_factory=list)
    attachments: list[MailAttachmentMeta] = Field(default_factory=list)
    delivery_state: DeliveryState = DeliveryState.DRAFT
    scheduled_for: datetime | None = None
    in_reply_to_id: str | None = None
    signature_disabled: bool = False
    version: int = 1
    last_saved_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "drafts"
        indexes = ["user_id"]


class RuleDoc(Document):
    """Mail rule — conditions + actions evaluated on inbound messages."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    user_id: str
    name: str
    enabled: bool = True
    conditions: list[RuleCondition] = Field(default_factory=list)
    actions: list[RuleAction] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "rules"
        indexes = ["user_id"]


class TemplateDoc(Document):
    """Reusable email template."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    user_id: str
    name: str
    subject: str = ""
    body_html: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "templates"
        indexes = ["user_id"]


class SignatureDoc(Document):
    """Email signature — one can be marked as default per user."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    user_id: str
    name: str
    body_html: str = ""
    is_default: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "signatures"
        indexes = ["user_id"]


class PreferencesDoc(Document):
    """User preferences — one document per user (upserted)."""
    id: str = Field(alias="_id")  # user_id is the _id  # type: ignore[assignment]
    density: Density = Density.COMFORTABLE
    reading_pane: ReadingPanePlacement = ReadingPanePlacement.RIGHT
    conversation_view: bool = True
    focused_inbox: bool = True
    default_sort: DefaultSort = DefaultSort.DATE_DESC
    preview_lines: int = 2
    theme: Theme = Theme.LIGHT
    default_reply: DefaultReply = DefaultReply.REPLY
    notifications: NotificationPrefs = Field(default_factory=NotificationPrefs)
    out_of_office: OutOfOfficePrefs = Field(default_factory=OutOfOfficePrefs)
    shortcuts_enabled: bool = True

    class Settings:
        name = "preferences"


class SavedSearchDoc(Document):
    """Saved search query for quick re-use."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    user_id: str
    name: str
    query: str = ""
    filters: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "saved_searches"
        indexes = ["user_id"]


class FavoritesDoc(Document):
    """User's favorite folder IDs — one document per user."""
    id: str = Field(alias="_id")  # user_id is the _id  # type: ignore[assignment]
    folder_ids: list[str] = Field(default_factory=list)

    class Settings:
        name = "favorites"


class DeliveryLogDoc(Document):
    """Audit trail for message delivery attempts."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    message_id: str
    draft_id: str | None = None
    state: DeliveryState
    transport_message_id: str | None = None
    diagnostic_code: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "delivery_log"
        indexes = ["message_id"]


# ── Convenience: list of all Beanie documents for init_beanie() ─────────────

ALL_DOCUMENTS = [
    UserDoc,
    FolderDoc,
    CategoryDoc,
    MessageDoc,
    ThreadDoc,
    DraftDoc,
    RuleDoc,
    TemplateDoc,
    SignatureDoc,
    PreferencesDoc,
    SavedSearchDoc,
    FavoritesDoc,
    DeliveryLogDoc,
]
