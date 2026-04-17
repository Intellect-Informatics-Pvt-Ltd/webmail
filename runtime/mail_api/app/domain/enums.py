"""PSense Mail — Domain enumerations.

These mirror the TypeScript types in webmail_ui/src/types/mail.ts.
"""
from __future__ import annotations

from enum import Enum


class DeliveryState(str, Enum):
    """Lifecycle state of an outbound message."""
    DRAFT = "draft"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_PERMANENT = "failed_permanent"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class FolderKind(str, Enum):
    """System folder types + custom."""
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


class Importance(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class MessageAction(str, Enum):
    """Actions that can be applied to one or more messages."""
    ARCHIVE = "archive"
    DELETE = "delete"
    RESTORE = "restore"
    MOVE = "move"
    MARK_READ = "mark_read"
    MARK_UNREAD = "mark_unread"
    FLAG = "flag"
    UNFLAG = "unflag"
    PIN = "pin"
    UNPIN = "unpin"
    SNOOZE = "snooze"
    UNSNOOZE = "unsnooze"
    CATEGORIZE = "categorize"
    UNCATEGORIZE = "uncategorize"


class RuleConditionField(str, Enum):
    SENDER = "sender"
    SUBJECT = "subject"
    HAS_ATTACHMENT = "hasAttachment"
    OLDER_THAN_DAYS = "olderThanDays"


class RuleConditionOp(str, Enum):
    CONTAINS = "contains"
    EQUALS = "equals"
    GT = "gt"


class RuleActionType(str, Enum):
    MOVE = "move"
    CATEGORIZE = "categorize"
    MARK_IMPORTANT = "markImportant"
    ARCHIVE = "archive"
    DELETE = "delete"


class Density(str, Enum):
    COMPACT = "compact"
    COMFORTABLE = "comfortable"
    SPACIOUS = "spacious"


class ReadingPanePlacement(str, Enum):
    RIGHT = "right"
    BOTTOM = "bottom"
    OFF = "off"


class Theme(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class DefaultSort(str, Enum):
    DATE_DESC = "date-desc"
    DATE_ASC = "date-asc"
    SENDER = "sender"
    SUBJECT = "subject"


class DefaultReply(str, Enum):
    REPLY = "reply"
    REPLY_ALL = "replyAll"


class OpLogKind(str, Enum):
    """Kind of operation recorded in the op-log for delta sync."""
    UPSERT = "upsert"
    DELETE = "delete"


class OpLogEntity(str, Enum):
    """Entity type recorded in op-log entries."""
    MESSAGE = "message"
    THREAD = "thread"
    FOLDER = "folder"
    CATEGORY = "category"
    RULE = "rule"
    TEMPLATE = "template"
    SIGNATURE = "signature"
    DRAFT = "draft"
    PREFERENCES = "preferences"
    SAVED_SEARCH = "saved_search"


class AccountRole(str, Enum):
    """Role of a user with respect to an account."""
    OWNER = "owner"
    DELEGATE_READ = "delegate_read"
    DELEGATE_SEND = "delegate_send"


class ProviderKind(str, Enum):
    """Mail provider type."""
    MEMORY = "memory"
    MAILPIT = "mailpit"
    GMAIL = "gmail"
    MICROSOFT_GRAPH = "microsoft_graph"


class AvState(str, Enum):
    """Antivirus scan state for attachments."""
    UNKNOWN = "unknown"
    CLEAN = "clean"
    INFECTED = "infected"
    SKIPPED = "skipped"


class PreviewState(str, Enum):
    """Attachment preview generation state."""
    NONE = "none"
    READY = "ready"
    FAILED = "failed"
