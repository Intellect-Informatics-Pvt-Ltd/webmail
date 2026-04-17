/**
 * Unit tests — Dexie schema
 *
 * Tests the PSenseMailDB class, its tables, and helper utilities.
 * Uses fake-indexeddb so no real browser storage is needed.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import "fake-indexeddb/auto"; // Polyfills indexedDB in jsdom
import { PSenseMailDB } from "../schema";
import { upsertMany, softDelete } from "../index";
import type { DBMessage, DBFolder, DBOutboxEntry, DBOpLogEntry } from "../schema";

let db: PSenseMailDB;
let _seq = 0;

beforeEach(async () => {
  _seq++;
  // Fresh named DB per test prevents fake-indexeddb state leaking
  db = new (class extends PSenseMailDB {
    constructor() {
      super();
      // Dexie uses `this.name` to identify the database
      Object.defineProperty(this, "name", { value: `psense-test-${_seq}`, writable: true });
    }
  })();
  await db.open();
});

afterEach(async () => {
  db.close();
  await db.delete();
});

const MSG_FIXTURE: DBMessage = {
  id: "msg-001",
  tenant_id: "default",
  account_id: "user-001",
  thread_id: "thr-001",
  folder_id: "inbox",
  subject: "Test subject",
  preview: "Test preview",
  sender: { name: "Alice", email: "alice@example.com" },
  recipients: [{ name: "Bob", email: "bob@example.com" }],
  received_at: "2025-01-01T00:00:00Z",
  is_read: false,
  is_flagged: false,
  is_pinned: false,
  has_attachments: false,
  has_mentions: false,
  importance: "normal",
  categories: [],
  is_draft: false,
  is_focused: false,
  trust_verified: false,
  delivery_state: "sent",
  version: 1,
  updated_at: "2025-01-01T00:00:00Z",
};

describe("PSenseMailDB schema", () => {
  describe("messages table", () => {
    it("can insert and retrieve a message", async () => {
      await db.messages.put(MSG_FIXTURE);
      const result = await db.messages.get("msg-001");
      expect(result?.subject).toBe("Test subject");
      expect(result?.sender.email).toBe("alice@example.com");
    });

    it("can query messages by folder_id", async () => {
      await db.messages.bulkPut([
        MSG_FIXTURE,
        { ...MSG_FIXTURE, id: "msg-002", folder_id: "archive" },
      ]);
      const inbox = await db.messages.where("folder_id").equals("inbox").toArray();
      expect(inbox).toHaveLength(1);
      expect(inbox[0].id).toBe("msg-001");
    });

    it("supports indexing by version", async () => {
      await db.messages.put(MSG_FIXTURE);
      const results = await db.messages.where("version").equals(1).toArray();
      expect(results).toHaveLength(1);
    });
  });

  describe("folders table", () => {
    const FOLDER: DBFolder = {
      id: "folder-001",
      tenant_id: "default",
      account_id: "user-001",
      name: "Projects",
      kind: "custom",
      system: false,
      sort_order: 10,
      unread_count: 0,
      total_count: 5,
      version: 1,
    };

    it("stores and retrieves a folder", async () => {
      await db.folders.put(FOLDER);
      const f = await db.folders.get("folder-001");
      expect(f?.name).toBe("Projects");
    });

    it("can query by kind", async () => {
      await db.folders.bulkPut([FOLDER, { ...FOLDER, id: "inbox-001", kind: "inbox" }]);
      const custom = await db.folders.where("kind").equals("custom").toArray();
      expect(custom[0].id).toBe("folder-001");
    });
  });

  describe("outbox table", () => {
    it("auto-increments id and stores an outbox entry", async () => {
      const entry: Omit<DBOutboxEntry, "id"> = {
        draft_id: "client-abc",
        account_id: "user-001",
        tenant_id: "default",
        to: [{ name: "Bob", email: "b@b.com" }],
        cc: [],
        bcc: [],
        subject: "Offline send test",
        body_html: "<p>Hello</p>",
        attachments: [],
        status: "queued",
        retry_count: 0,
        idempotency_key: "idem-001",
        created_at: "2025-01-01T00:00:00Z",
        updated_at: "2025-01-01T00:00:00Z",
      };
      const id = await db.outbox.add(entry as DBOutboxEntry);
      expect(id).toBeGreaterThan(0);

      const stored = await db.outbox.get(id);
      expect(stored?.subject).toBe("Offline send test");
      expect(stored?.status).toBe("queued");
    });

    it("can query pending entries by account_id", async () => {
      await db.outbox.add({
        draft_id: "d1", account_id: "user-001", tenant_id: "default",
        to: [], cc: [], bcc: [], subject: "S1", body_html: "", attachments: [],
        status: "queued", retry_count: 0, idempotency_key: "k1",
        created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      } as DBOutboxEntry);
      await db.outbox.add({
        draft_id: "d2", account_id: "user-002", tenant_id: "default",
        to: [], cc: [], bcc: [], subject: "S2", body_html: "", attachments: [],
        status: "queued", retry_count: 0, idempotency_key: "k2",
        created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      } as DBOutboxEntry);

      const forUser1 = await db.outbox.where("account_id").equals("user-001").toArray();
      expect(forUser1).toHaveLength(1);
    });
  });

  describe("op_log table", () => {
    it("stores a client op-log entry", async () => {
      const entry: Omit<DBOpLogEntry, "id"> = {
        account_id: "user-001",
        tenant_id: "default",
        entity: "message",
        entity_id: "msg-001",
        action: "archive",
        payload: { destination_folder_id: "archive" },
        optimistic_patch: { folder_id: "archive" },
        idempotency_key: "op-key-001",
        status: "pending",
        retry_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      const id = await db.op_log.add(entry as DBOpLogEntry);
      const stored = await db.op_log.get(id);
      expect(stored?.action).toBe("archive");
      expect(stored?.status).toBe("pending");
    });

    it("can update status to sent", async () => {
      const id = await db.op_log.add({
        account_id: "user-001", tenant_id: "default",
        entity: "message", entity_id: "msg-002",
        action: "mark_read", payload: {}, optimistic_patch: { is_read: true },
        idempotency_key: "op-key-002", status: "pending", retry_count: 0,
        created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      } as DBOpLogEntry);
      await db.op_log.update(id, { status: "sent" });
      const updated = await db.op_log.get(id);
      expect(updated?.status).toBe("sent");
    });
  });

  describe("sync_cursors table", () => {
    it("stores and retrieves a sync cursor", async () => {
      await db.sync_cursors.put({
        account_id: "user-001",
        cursor: "abc123",
        synced_at: new Date().toISOString(),
      });
      const row = await db.sync_cursors.get("user-001");
      expect(row?.cursor).toBe("abc123");
    });

    it("updates an existing cursor", async () => {
      await db.sync_cursors.put({ account_id: "user-001", cursor: "v1", synced_at: "t1" });
      await db.sync_cursors.put({ account_id: "user-001", cursor: "v2", synced_at: "t2" });
      const row = await db.sync_cursors.get("user-001");
      expect(row?.cursor).toBe("v2");
    });
  });

  describe("upsertMany helper", () => {
    it("bulk-inserts messages", async () => {
      const msgs: DBMessage[] = [
        { ...MSG_FIXTURE, id: "bulk-1" },
        { ...MSG_FIXTURE, id: "bulk-2" },
      ];
      await upsertMany(db.messages, msgs);
      expect(await db.messages.count()).toBe(2);
    });

    it("replaces existing record on conflict (upsert semantics)", async () => {
      await db.messages.put({ ...MSG_FIXTURE, is_read: false });
      await upsertMany(db.messages, [{ ...MSG_FIXTURE, is_read: true }]);
      const result = await db.messages.get("msg-001");
      expect(result?.is_read).toBe(true);
    });

    it("no-ops on empty array", async () => {
      await expect(upsertMany(db.messages, [])).resolves.not.toThrow();
    });
  });

  describe("softDelete helper", () => {
    it("marks deleted_at without removing the record", async () => {
      await db.messages.put(MSG_FIXTURE);
      await softDelete(db.messages, "msg-001");
      const result = await db.messages.get("msg-001");
      expect(result).toBeDefined();
      expect(result?.deleted_at).toBeDefined();
    });
  });
});
