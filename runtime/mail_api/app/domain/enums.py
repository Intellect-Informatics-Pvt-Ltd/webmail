"""PSense Mail — Domain enumerations.

These mirror the TypeScript types in webmail_ui/src/types/mail.ts and the
reference enums in thoughts/shared/plans/mail_facade_reference.py.
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
