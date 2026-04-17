export type MailFolderId =
  | "inbox"
  | "focused"
  | "other"
  | "drafts"
  | "sent"
  | "archive"
  | "snoozed"
  | "flagged"
  | "deleted"
  | "junk";

export type Importance = "low" | "normal" | "high";

export interface MailRecipient {
  name: string;
  email: string;
  avatarColor?: string;
}

export interface MailAttachment {
  id: string;
  name: string;
  size: number; // bytes
  mime: string;
}

export interface MailCategory {
  id: string;
  name: string;
  color: string; // tailwind color name (semantic-only consumed in component)
}

export interface MailFolder {
  id: string;
  name: string;
  icon?: string;
  system?: boolean;
  parentId?: string;
}

export interface MailMessage {
  id: string;
  threadId: string;
  folderId: MailFolderId | string; // system or custom
  subject: string;
  preview: string;
  bodyHtml: string;
  sender: MailRecipient;
  recipients: MailRecipient[];
  cc?: MailRecipient[];
  bcc?: MailRecipient[];
  receivedAt: string; // ISO
  isRead: boolean;
  isFlagged: boolean;
  isPinned: boolean;
  hasAttachments: boolean;
  importance: Importance;
  categories: string[]; // category ids
  snoozedUntil?: string;
  scheduledFor?: string;
  isDraft?: boolean;
  isFocused?: boolean;
  hasMentions?: boolean;
  attachments?: MailAttachment[];
  trustVerified?: boolean;
}

export interface MailThread {
  id: string;
  subject: string;
  participantEmails: string[];
  messageIds: string[];
  lastReceivedAt: string;
  unreadCount: number;
  hasAttachments: boolean;
  isFlagged: boolean;
  folderId: MailFolderId | string;
}

export type RuleAction =
  | { type: "move"; folderId: string }
  | { type: "categorize"; categoryId: string }
  | { type: "markImportant" }
  | { type: "archive" }
  | { type: "delete" };

export interface MailRule {
  id: string;
  name: string;
  enabled: boolean;
  conditions: Array<
    | { field: "sender"; op: "contains" | "equals"; value: string }
    | { field: "subject"; op: "contains"; value: string }
    | { field: "hasAttachment"; op: "equals"; value: boolean }
    | { field: "olderThanDays"; op: "gt"; value: number }
  >;
  actions: RuleAction[];
}

export interface SavedSearch {
  id: string;
  name: string;
  query: string;
  filters: Record<string, unknown>;
}

export interface MailTemplate {
  id: string;
  name: string;
  subject: string;
  bodyHtml: string;
}

export interface MailSignature {
  id: string;
  name: string;
  bodyHtml: string;
  isDefault?: boolean;
}

export type Density = "compact" | "comfortable" | "spacious";
export type ReadingPanePlacement = "right" | "bottom" | "off";
export type Theme = "light" | "dark" | "system";

export interface UserPreferences {
  density: Density;
  readingPane: ReadingPanePlacement;
  conversationView: boolean;
  focusedInbox: boolean;
  defaultSort: "date-desc" | "date-asc" | "sender" | "subject";
  previewLines: 1 | 2 | 3;
  theme: Theme;
  defaultReply: "reply" | "replyAll";
  notifications: {
    desktop: boolean;
    sound: boolean;
    onlyFocused: boolean;
  };
  outOfOffice: {
    enabled: boolean;
    message: string;
  };
  shortcutsEnabled: boolean;
}

export interface ComposeDraft {
  id: string;
  to: MailRecipient[];
  cc: MailRecipient[];
  bcc: MailRecipient[];
  subject: string;
  bodyHtml: string;
  showCc: boolean;
  showBcc: boolean;
  expanded: boolean; // floating vs full-screen
  minimized?: boolean; // collapsed to title bar only
  scheduledFor?: string;
  attachments: MailAttachment[];
  lastSavedAt?: string;
  inReplyToId?: string;
  signatureDisabled?: boolean; // per-message opt-out from auto-appended default signature
}
