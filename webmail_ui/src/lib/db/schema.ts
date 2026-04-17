/**
 * PSense Mail — Dexie (IndexedDB) schema.
 *
 * The schema mirrors the server-side domain models.
 * Every table that participates in offline sync has:
 *   - id (primary key)
 *   - version (monotonic int for optimistic concurrency)
 *   - deleted_at? (tombstone for soft-delete)
 *
 * Naming: snake_case keys match the server OpenAPI output.
 * The only exception is the compound index syntax Dexie uses ([a+b]).
 *
 * IMPORTANT: Only bump the Dexie version number when the schema changes —
 * never edit an existing version's store definition.
 */

import Dexie, { type EntityTable } from "dexie";

// ── Mirrored entity shapes ───────────────────────────────────────────────────

export interface DBMessage {
  id: string;
  tenant_id: string;
  account_id: string;
  thread_id: string;
  folder_id: string;
  subject: string;
  preview: string;
  body_html?: string | null;
  body_text?: string | null;
  sender: { name: string; email: string; avatar_color?: string | null };
  recipients: Array<{ name: string; email: string }>;
  cc?: Array<{ name: string; email: string }>;
  bcc?: Array<{ name: string; email: string }>;
  received_at: string | null;
  is_read: boolean;
  is_flagged: boolean;
  is_pinned: boolean;
  has_attachments: boolean;
  has_mentions: boolean;
  importance: "low" | "normal" | "high";
  categories: string[];
  is_draft: boolean;
  is_focused: boolean;
  trust_verified: boolean;
  external?: boolean;
  first_time_sender?: boolean;
  snoozed_until?: string | null;
  scheduled_for?: string | null;
  delivery_state: string;
  version: number;
  updated_at: string;
  deleted_at?: string | null;
}

export interface DBThread {
  id: string;
  tenant_id: string;
  account_id: string;
  subject: string;
  folder_id: string;
  participant_emails: string[];
  message_ids: string[];
  last_message_at: string | null;
  unread_count: number;
  total_count: number;
  has_attachments: boolean;
  is_flagged: boolean;
  version: number;
  deleted_at?: string | null;
}

export interface DBFolder {
  id: string;
  tenant_id: string;
  account_id: string;
  name: string;
  kind: string;
  system: boolean;
  parent_id?: string | null;
  sort_order: number;
  icon?: string | null;
  color?: string | null;
  unread_count: number;
  total_count: number;
  version: number;
  deleted_at?: string | null;
}

export interface DBCategory {
  id: string;
  tenant_id: string;
  account_id: string;
  name: string;
  color: string;
  version: number;
  deleted_at?: string | null;
}

export interface DBRule {
  id: string;
  tenant_id: string;
  account_id: string;
  name: string;
  enabled: boolean;
  conditions: unknown[];
  actions: unknown[];
  version: number;
  deleted_at?: string | null;
}

export interface DBTemplate {
  id: string;
  tenant_id: string;
  account_id: string;
  name: string;
  subject: string;
  body_html: string;
  version: number;
  deleted_at?: string | null;
}

export interface DBSignature {
  id: string;
  tenant_id: string;
  account_id: string;
  name: string;
  body_html: string;
  is_default: boolean;
  version: number;
  deleted_at?: string | null;
}

export interface DBSavedSearch {
  id: string;
  tenant_id: string;
  account_id: string;
  name: string;
  query: string;
  filters: Record<string, unknown>;
  version: number;
  deleted_at?: string | null;
}

export interface DBPreferences {
  id: string; // user_id
  tenant_id: string;
  account_id: string;
  density: string;
  reading_pane: string;
  conversation_view: boolean;
  focused_inbox: boolean;
  default_sort: string;
  preview_lines: number;
  theme: string;
  default_reply: string;
  notifications: {
    desktop: boolean;
    sound: boolean;
    only_focused: boolean;
    push_enabled: boolean;
    quiet_hours_start?: string | null;
    quiet_hours_end?: string | null;
  };
  out_of_office: { enabled: boolean; message: string; start?: string | null; end?: string | null };
  shortcuts_enabled: boolean;
  version: number;
}

export interface DBAttachmentMeta {
  id: string;
  message_id: string;
  name: string;
  size: number;
  mime: string;
  av_state: string;
  preview_state: string;
  version: number;
}

export interface DBAttachmentBlob {
  id: string;       // attachment id
  blob: Blob;
  cached_at: string;
}

/** Compose draft in the outbox — waiting to be sent */
export interface DBOutboxEntry {
  id?: number;          // auto-increment
  draft_id: string;     // maps to draft in server (pre-created) or client-only
  account_id: string;
  tenant_id: string;
  to: Array<{ name: string; email: string }>;
  cc: Array<{ name: string; email: string }>;
  bcc: Array<{ name: string; email: string }>;
  subject: string;
  body_html: string;
  attachments: Array<{ name: string; size: number; mime: string; blob_id?: string }>;
  in_reply_to_id?: string | null;
  scheduled_for?: string | null;
  status: "pending" | "queued" | "sending" | "failed" | "sent";
  retry_count: number;
  last_error?: string | null;
  idempotency_key: string;
  created_at: string;
  updated_at: string;
}

/** Pending mutation that needs to reach the server (Tier 3 op-log) */
export interface DBOpLogEntry {
  id?: number;          // auto-increment
  account_id: string;
  tenant_id: string;
  entity: string;       // "message" | "thread" | "folder" | ...
  entity_id: string;
  action: string;       // "archive" | "mark_read" | "move" | ...
  payload: Record<string, unknown>;
  optimistic_patch: Record<string, unknown>;
  idempotency_key: string;
  status: "pending" | "sent" | "failed" | "conflict";
  retry_count: number;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

/** Per-account sync cursor for delta sync (Tier 4) */
export interface DBSyncCursor {
  account_id: string;   // primary key
  cursor: string;
  synced_at: string;
}

/** Generic key-value meta store (used by TanStack Query persister) */
export interface DBMeta {
  key: string;
  value: string;
  updated_at: string;
}

// ── Dexie database class ─────────────────────────────────────────────────────

export class PSenseMailDB extends Dexie {
  messages!: EntityTable<DBMessage, "id">;
  threads!: EntityTable<DBThread, "id">;
  folders!: EntityTable<DBFolder, "id">;
  categories!: EntityTable<DBCategory, "id">;
  rules!: EntityTable<DBRule, "id">;
  templates!: EntityTable<DBTemplate, "id">;
  signatures!: EntityTable<DBSignature, "id">;
  saved_searches!: EntityTable<DBSavedSearch, "id">;
  preferences!: EntityTable<DBPreferences, "id">;
  attachments_meta!: EntityTable<DBAttachmentMeta, "id">;
  attachments_blobs!: EntityTable<DBAttachmentBlob, "id">;
  outbox!: EntityTable<DBOutboxEntry, "id">;
  op_log!: EntityTable<DBOpLogEntry, "id">;
  sync_cursors!: EntityTable<DBSyncCursor, "account_id">;
  meta!: EntityTable<DBMeta, "key">;

  constructor() {
    super("psense-mail-v1");

    this.version(1).stores({
      messages: "&id, tenant_id, account_id, folder_id, thread_id, received_at, version, deleted_at",
      threads: "&id, tenant_id, account_id, folder_id, last_message_at, version",
      folders: "&id, tenant_id, account_id, kind, version",
      categories: "&id, tenant_id, account_id, version",
      rules: "&id, tenant_id, account_id, version",
      templates: "&id, tenant_id, account_id, version",
      signatures: "&id, tenant_id, account_id, version",
      saved_searches: "&id, tenant_id, account_id, version",
      preferences: "&id",
      attachments_meta: "&id, message_id, version",
      attachments_blobs: "&id",
      outbox: "++id, account_id, status, created_at",
      op_log: "++id, account_id, entity, entity_id, status, created_at",
      sync_cursors: "&account_id",
      meta: "&key",
    });
  }
}
