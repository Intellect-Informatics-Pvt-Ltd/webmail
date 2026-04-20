"""PSense Mail — Domain models (Beanie Documents for MongoDB).

Every model maps 1:1 to a MongoDB collection.

TENANCY CONTRACT
----------------
Every mutable collection carries:
  - tenant_id  : str  — top-level isolation boundary (org/workspace)
  - account_id : str  — mail identity (avery@psense.ai)
  - version    : int  — monotonic increment on every write (optimistic concurrency)
  - deleted_at : datetime | None — soft-delete tombstone (hard-purge by retention worker)

Defaults of "default" for tenant_id and user_id for account_id ensure backward
compatibility with existing dev/test seed data while the migration path is additive.

IDEMPOTENCY
-----------
IdempotencyRecord stores request keys for 24 h so duplicate POST/PATCH/DELETE
requests return the cached response without re-executing.

OP-LOG (DELTA SYNC)
-------------------
OpLogEntry is an append-only change feed per (tenant_id, account_id) ordered by
monotonic `seq`. The delta sync endpoint streams it to clients for offline sync.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any

from beanie import Document, Indexed, before_event, Replace, Insert
from pydantic import BaseModel, Field, field_validator
from ulid import ULID

from app.domain.enums import (
    AccountRole,
    AvState,
    DefaultReply,
    DefaultSort,
    Density,
    DeliveryState,
    FolderKind,
    Importance,
    OpLogEntity,
    OpLogKind,
    PreviewState,
    ProviderKind,
    ReadingPanePlacement,
    RuleActionType,
    RuleConditionField,
    RuleConditionOp,
    Theme,
)


def _new_id() -> str:
    """Generate a sortable ULID string."""
    return str(ULID())


def _now() -> datetime:
    return datetime.utcnow()


_logger = logging.getLogger(__name__)


def _get_fernet():
    """Lazy-load Fernet cipher from settings."""
    from config.settings import get_settings
    key = get_settings().security.credential_encryption_key
    if not key:
        return None
    from cryptography.fernet import Fernet
    return Fernet(key.encode() if isinstance(key, str) else key)


# ── Embedded sub-documents ───────────────────────────────────────────────────


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
    storage_path: str | None = None
    av_state: AvState = AvState.UNKNOWN
    preview_state: PreviewState = PreviewState.NONE
    adapter_meta: dict[str, Any] = Field(default_factory=dict)


class RuleCondition(BaseModel):
    field: RuleConditionField
    op: RuleConditionOp
    value: str | bool | int


class RuleAction(BaseModel):
    type: RuleActionType
    folder_id: str | None = None
    category_id: str | None = None


class NotificationPrefs(BaseModel):
    desktop: bool = True
    sound: bool = False
    only_focused: bool = True
    push_enabled: bool = False
    quiet_hours_start: str | None = None  # "22:00"
    quiet_hours_end: str | None = None    # "07:00"


class OutOfOfficePrefs(BaseModel):
    enabled: bool = False
    message: str = ""
    start: datetime | None = None
    end: datetime | None = None


class AuthenticationResults(BaseModel):
    """SPF/DKIM/DMARC pass/fail from Authentication-Results header."""
    spf: str | None = None      # pass | fail | neutral | softfail | none
    dkim: str | None = None
    dmarc: str | None = None
    raw: str | None = None


# ── Identity / tenancy documents ─────────────────────────────────────────────


class TenantDoc(Document):
    """An organization or workspace — the top-level isolation boundary."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    slug: str  # short identifier, unique
    name: str
    domains: list[str] = Field(default_factory=list)  # e.g. ["psense.ai"]
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    version: int = 1

    class Settings:
        name = "tenants"
        indexes = [
            [("slug", 1)],
        ]


class UserDoc(Document):
    """Represents a user profile (populated from KeyCloak on first login)."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    oidc_subject: str | None = None  # from KeyCloak (sub claim)
    email: str
    display_name: str = ""
    avatar_url: str | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    version: int = 1

    class Settings:
        name = "users"
        indexes = [
            "email",
            [("tenant_id", 1), ("email", 1)],
        ]


class AccountDoc(Document):
    """A mail identity belonging to a user (e.g. avery@psense.ai).

    A user can have multiple accounts. provider_meta holds encrypted credentials
    (refresh tokens, OAuth state) — never returned in API responses.
    """
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    owner_user_id: str
    address: str       # "avery@psense.ai"
    display_name: str = ""
    provider: ProviderKind = ProviderKind.MEMORY
    provider_meta: dict[str, Any] = Field(default_factory=dict)
    provider_meta_enc: str | None = None  # Fernet-encrypted provider_meta
    is_primary: bool = True
    sync_cursor: str | None = None  # provider delta cursor
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    version: int = 1
    deleted_at: datetime | None = None

    @before_event(Insert, Replace)
    def encrypt_provider_meta(self) -> None:
        """Encrypt provider_meta before persistence using Fernet."""
        fernet = _get_fernet()
        if fernet and self.provider_meta:
            plaintext = json.dumps(self.provider_meta).encode()
            self.provider_meta_enc = fernet.encrypt(plaintext).decode()
            self.provider_meta = {}  # Clear plaintext for storage

    def decrypt_provider_meta(self) -> None:
        """Decrypt provider_meta_enc back to provider_meta dict."""
        if self.provider_meta_enc:
            fernet = _get_fernet()
            if fernet:
                try:
                    plaintext = fernet.decrypt(self.provider_meta_enc.encode())
                    self.provider_meta = json.loads(plaintext)
                except Exception:
                    _logger.warning("Failed to decrypt provider_meta for account %s", self.id)

    class Settings:
        name = "accounts"
        indexes = [
            [("tenant_id", 1), ("owner_user_id", 1)],
            [("tenant_id", 1), ("address", 1)],
        ]


class AccountUserDoc(Document):
    """Association between an account and an authorized user (owner or delegate)."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str
    user_id: str
    role: AccountRole = AccountRole.OWNER
    created_at: datetime = Field(default_factory=_now)

    class Settings:
        name = "account_users"
        indexes = [
            [("account_id", 1), ("user_id", 1)],
            "user_id",
        ]


# ── Mail documents ────────────────────────────────────────────────────────────


class FolderDoc(Document):
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    user_id: str  # kept for backward compat; prefer account_id going forward
    name: str
    kind: FolderKind = FolderKind.CUSTOM
    system: bool = False
    parent_id: str | None = None
    sort_order: int = 0
    icon: str | None = None
    color: str | None = None
    version: int = 1
    deleted_at: datetime | None = None

    class Settings:
        name = "folders"
        indexes = [
            [("user_id", 1), ("kind", 1)],
            [("tenant_id", 1), ("account_id", 1), ("kind", 1)],
        ]


class CategoryDoc(Document):
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    user_id: str
    name: str
    color: str
    version: int = 1
    deleted_at: datetime | None = None

    class Settings:
        name = "categories"
        indexes = [
            "user_id",
            [("tenant_id", 1), ("account_id", 1)],
        ]


class MessageDoc(Document):
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    user_id: str
    thread_id: str
    folder_id: str
    # RFC 2822 header fields
    message_id_header: str | None = None   # Message-ID header value
    in_reply_to_header: str | None = None  # In-Reply-To header value
    references_headers: list[str] = Field(default_factory=list)
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
    external: bool = False           # sender outside tenant domains
    first_time_sender: bool = False  # never corresponded before
    authentication_results: AuthenticationResults | None = None
    in_reply_to_id: str | None = None  # internal PSense message id
    delivery_state: DeliveryState = DeliveryState.SENT
    version: int = 1
    adapter_meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    deleted_at: datetime | None = None

    class Settings:
        name = "messages"
        indexes = [
            [("user_id", 1), ("folder_id", 1), ("received_at", -1)],
            [("user_id", 1), ("thread_id", 1)],
            [("user_id", 1), ("is_read", 1)],
            [("user_id", 1), ("is_flagged", 1)],
            [("user_id", 1), ("is_pinned", 1)],
            [("user_id", 1), ("categories", 1)],
            [("tenant_id", 1), ("account_id", 1), ("folder_id", 1), ("received_at", -1)],
            [("tenant_id", 1), ("account_id", 1), ("updated_at", -1)],
            # Sparse unique index on RFC 2822 Message-ID for dedup
            [("message_id_header", 1)],
        ]


class ThreadDoc(Document):
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
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
    version: int = 1
    deleted_at: datetime | None = None

    class Settings:
        name = "threads"
        indexes = [
            [("user_id", 1), ("folder_id", 1), ("last_message_at", -1)],
            [("tenant_id", 1), ("account_id", 1), ("folder_id", 1), ("last_message_at", -1)],
            [("tenant_id", 1), ("account_id", 1), ("updated_at", -1)],
        ]


class DraftDoc(Document):
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
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
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    deleted_at: datetime | None = None

    class Settings:
        name = "drafts"
        indexes = [
            "user_id",
            [("tenant_id", 1), ("account_id", 1)],
        ]


class RuleDoc(Document):
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    user_id: str
    name: str
    enabled: bool = True
    conditions: list[RuleCondition] = Field(default_factory=list)
    actions: list[RuleAction] = Field(default_factory=list)
    version: int = 1
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    deleted_at: datetime | None = None

    class Settings:
        name = "rules"
        indexes = [
            "user_id",
            [("tenant_id", 1), ("account_id", 1)],
        ]


class TemplateDoc(Document):
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    user_id: str
    name: str
    subject: str = ""
    body_html: str = ""
    version: int = 1
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    deleted_at: datetime | None = None

    class Settings:
        name = "templates"
        indexes = [
            "user_id",
            [("tenant_id", 1), ("account_id", 1)],
        ]


class SignatureDoc(Document):
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    user_id: str
    name: str
    body_html: str = ""
    is_default: bool = False
    version: int = 1
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    deleted_at: datetime | None = None

    class Settings:
        name = "signatures"
        indexes = [
            "user_id",
            [("tenant_id", 1), ("account_id", 1)],
        ]


class PreferencesDoc(Document):
    """User preferences — one document per user (upserted on user_id)."""
    id: str = Field(alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
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
    version: int = 1
    updated_at: datetime = Field(default_factory=_now)

    class Settings:
        name = "preferences"


class SavedSearchDoc(Document):
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    user_id: str
    name: str
    query: str = ""
    filters: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    deleted_at: datetime | None = None

    class Settings:
        name = "saved_searches"
        indexes = [
            "user_id",
            [("tenant_id", 1), ("account_id", 1)],
        ]


class FavoritesDoc(Document):
    """User's favorite folder IDs — one document per user."""
    id: str = Field(alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    folder_ids: list[str] = Field(default_factory=list)

    class Settings:
        name = "favorites"


class DeliveryLogDoc(Document):
    """Audit trail for message delivery attempts."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    message_id: str
    draft_id: str | None = None
    state: DeliveryState
    transport_message_id: str | None = None
    diagnostic_code: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=_now)

    class Settings:
        name = "delivery_log"
        indexes = [
            "message_id",
            [("tenant_id", 1), ("account_id", 1), ("timestamp", -1)],
        ]


class IdempotencyRecord(Document):
    """Idempotency deduplication record.

    Stores the key + cached response so duplicate requests within 24 h
    return the same result without re-executing. TTL index auto-expires.
    """
    id: str = Field(alias="_id")  # idempotency_key is the _id  # type: ignore[assignment]
    tenant_id: str = "default"
    user_id: str
    account_id: str = ""
    operation: str  # e.g. "send_draft", "apply_action"
    request_hash: str = ""
    response_json: str = ""
    created_at: datetime = Field(default_factory=_now)
    expires_at: datetime | None = None  # set to created_at + 24h by the service

    class Settings:
        name = "idempotency_records"
        indexes = [
            [("tenant_id", 1), ("user_id", 1)],
            "expires_at",  # TTL index — Mongo needs a TTL policy set externally
        ]


class OpLogEntry(Document):
    """Server-side change-feed entry for delta sync.

    Written transactionally alongside every mutating operation.
    Clients consume via GET /api/v1/sync?since=<cursor>.
    seq is a monotonic int64 derived from millisecond timestamp + counter.
    """
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    seq: int = Field(default_factory=lambda: int(time.time() * 1000))
    kind: OpLogKind
    entity: OpLogEntity
    entity_id: str
    payload: dict[str, Any] = Field(default_factory=dict)  # full entity projection
    created_at: datetime = Field(default_factory=_now)

    class Settings:
        name = "op_log"
        indexes = [
            [("tenant_id", 1), ("account_id", 1), ("seq", 1)],
            [("tenant_id", 1), ("account_id", 1), ("entity", 1), ("entity_id", 1)],
            "created_at",  # TTL: retain 90 days
        ]


class AuditLogDoc(Document):
    """Append-only audit trail for admin/compliance — Phase 4."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    user_id: str
    action: str
    subject_type: str  # "message", "folder", etc.
    subject_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    ip: str | None = None
    user_agent: str | None = None
    correlation_id: str | None = None
    created_at: datetime = Field(default_factory=_now)

    class Settings:
        name = "audit_log"
        indexes = [
            [("tenant_id", 1), ("created_at", -1)],
            [("tenant_id", 1), ("user_id", 1), ("created_at", -1)],
            "created_at",  # TTL: 90 days by default
        ]


class FeatureFlagDoc(Document):
    """Feature flag — Phase 5.

    Strategy can be: "disabled", "enabled", "percentage", "allowlist".
    """
    id: str = Field(alias="_id")  # key is the _id  # type: ignore[assignment]
    enabled: bool = False
    rollout_strategy: str = "disabled"  # "disabled" | "enabled" | "percentage" | "allowlist"
    rollout_percentage: int = 0
    tenant_allowlist: list[str] = Field(default_factory=list)
    user_allowlist: list[str] = Field(default_factory=list)
    description: str = ""
    updated_at: datetime = Field(default_factory=_now)

    class Settings:
        name = "feature_flags"


class SequenceDoc(Document):
    """Atomic counter for monotonic op-log sequencing.

    One document per (tenant_id, account_id) pair. The seq field is
    incremented atomically via findAndModify ($inc) on every op-log append.
    """
    id: str = Field(alias="_id")  # type: ignore[assignment]  # "{tenant_id}:{account_id}"
    seq: int = 0

    class Settings:
        name = "sequences"


class DeadLetterDoc(Document):
    """Dead-letter queue entry for failed async jobs."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    queue: str = ""  # e.g., "inbound_poll", "send_retry", "av_scan"
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=_now)
    last_attempt_at: datetime | None = None
    resolved_at: datetime | None = None

    class Settings:
        name = "dead_letters"
        indexes = [
            [("tenant_id", 1), ("queue", 1), ("created_at", -1)],
            "resolved_at",
        ]


class ContactDoc(Document):
    """Contact entry for the address book."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    user_id: str
    email: str
    display_name: str = ""
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    job_title: str = ""
    phone: str = ""
    avatar_url: str | None = None
    notes: str = ""
    groups: list[str] = Field(default_factory=list)
    is_favorite: bool = False
    last_contacted_at: datetime | None = None
    version: int = 1
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    deleted_at: datetime | None = None

    class Settings:
        name = "contacts"
        indexes = [
            [("user_id", 1), ("email", 1)],
            [("tenant_id", 1), ("account_id", 1)],
            [("user_id", 1), ("display_name", 1)],
        ]


class CalendarEventDoc(Document):
    """Calendar event."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    account_id: str = ""
    user_id: str
    title: str
    description: str = ""
    location: str = ""
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    recurrence_rule: str | None = None  # RFC 5545 RRULE
    attendees: list[MailRecipient] = Field(default_factory=list)
    organizer: MailRecipient | None = None
    calendar_id: str = "default"
    color: str | None = None
    reminder_minutes: int | None = None
    ical_uid: str | None = None  # iCalendar UID for dedup
    version: int = 1
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    deleted_at: datetime | None = None

    class Settings:
        name = "calendar_events"
        indexes = [
            [("user_id", 1), ("start_time", 1)],
            [("tenant_id", 1), ("account_id", 1), ("start_time", 1)],
            "ical_uid",
        ]


class MigrationDoc(Document):
    """Schema migration record — tracks applied migrations."""
    id: str = Field(alias="_id")  # type: ignore[assignment]  # migration name
    applied_at: datetime = Field(default_factory=_now)
    duration_ms: float = 0.0
    description: str = ""
    rollback_possible: bool = False

    class Settings:
        name = "migrations"


class WebhookSubscriptionDoc(Document):
    """Webhook subscription for event notifications."""
    id: str = Field(default_factory=_new_id, alias="_id")  # type: ignore[assignment]
    tenant_id: str = "default"
    url: str
    events: list[str] = Field(default_factory=list)  # e.g., ["message.received", "message.sent"]
    secret: str = ""  # HMAC-SHA256 secret
    active: bool = True
    failure_count: int = 0
    last_delivered_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    class Settings:
        name = "webhook_subscriptions"
        indexes = [
            [("tenant_id", 1), ("active", 1)],
        ]


# ── Convenience: all Beanie document models for init_beanie() ────────────────

ALL_DOCUMENTS = [
    # Identity / tenancy
    TenantDoc,
    UserDoc,
    AccountDoc,
    AccountUserDoc,
    # Mail
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
    # Contacts & Calendar
    ContactDoc,
    CalendarEventDoc,
    # Infrastructure
    DeliveryLogDoc,
    IdempotencyRecord,
    OpLogEntry,
    AuditLogDoc,
    FeatureFlagDoc,
    SequenceDoc,
    DeadLetterDoc,
    MigrationDoc,
    WebhookSubscriptionDoc,
]
