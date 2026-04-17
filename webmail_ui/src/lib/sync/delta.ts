/**
 * PSense Mail — Delta sync engine (Tier 4 offline).
 *
 * Polls GET /api/v1/sync?since=<cursor> and replays op-log entries into:
 *   1. Dexie (IDB) for durable cache
 *   2. TanStack Query in-memory cache for live UI updates
 *
 * After the delta replay, the client op-log drain runs to flush any
 * pending local mutations that accumulated while offline.
 *
 * Cursor lifecycle:
 *   - Stored per account_id in `sync_cursors` Dexie table.
 *   - "0" = full sync from beginning.
 *   - Updated after each successful delta batch.
 *
 * Conflict resolution:
 *   - UPSERT ops: overwrite IDB + Query cache (server is authoritative).
 *   - DELETE ops: soft-delete in IDB; invalidate relevant queries.
 */

import type { QueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { db, upsertMany } from "@/lib/db/index";
import type {
  DBMessage, DBThread, DBFolder, DBCategory,
  DBRule, DBTemplate, DBSignature, DBSavedSearch,
} from "@/lib/db/schema";
import { keys, type KeyContext } from "@/lib/query/keys";
import { drainOpLog } from "./op-log";

// ── Types matching the /api/v1/sync response ──────────────────────────────────

interface SyncOp {
  seq: number;
  kind: "upsert" | "delete";
  entity: string;
  id: string;
  payload: Record<string, unknown>;
}

interface SyncResponse {
  next_cursor: string;
  ops: SyncOp[];
  has_more: boolean;
}

// ── Delta replay ──────────────────────────────────────────────────────────────

async function applyOps(ops: SyncOp[], ctx: KeyContext, queryClient: QueryClient): Promise<void> {
  // Group ops by entity type for batch IDB writes
  const byEntity: Record<string, SyncOp[]> = {};
  for (const op of ops) {
    (byEntity[op.entity] ??= []).push(op);
  }

  for (const [entity, entityOps] of Object.entries(byEntity)) {
    const upserts = entityOps.filter((o) => o.kind === "upsert").map((o) => o.payload);
    const deletes = entityOps.filter((o) => o.kind === "delete").map((o) => o.id);

    switch (entity) {
      case "message": {
        if (upserts.length) await upsertMany(db.messages, upserts as DBMessage[]);
        for (const id of deletes) await db.messages.update(id, { deleted_at: new Date().toISOString() });
        queryClient.invalidateQueries({ queryKey: keys.messages.all(ctx) });
        break;
      }
      case "thread": {
        if (upserts.length) await upsertMany(db.threads, upserts as DBThread[]);
        for (const id of deletes) await db.threads.update(id, { deleted_at: new Date().toISOString() });
        queryClient.invalidateQueries({ queryKey: keys.threads.all(ctx) });
        break;
      }
      case "folder": {
        if (upserts.length) await upsertMany(db.folders, upserts as DBFolder[]);
        for (const id of deletes) await db.folders.update(id, { deleted_at: new Date().toISOString() });
        queryClient.invalidateQueries({ queryKey: keys.folders.all(ctx) });
        break;
      }
      case "category": {
        if (upserts.length) await upsertMany(db.categories, upserts as DBCategory[]);
        queryClient.invalidateQueries({ queryKey: keys.categories.all(ctx) });
        break;
      }
      case "rule": {
        if (upserts.length) await upsertMany(db.rules, upserts as DBRule[]);
        queryClient.invalidateQueries({ queryKey: keys.rules.all(ctx) });
        break;
      }
      case "template": {
        if (upserts.length) await upsertMany(db.templates, upserts as DBTemplate[]);
        queryClient.invalidateQueries({ queryKey: keys.templates.all(ctx) });
        break;
      }
      case "signature": {
        if (upserts.length) await upsertMany(db.signatures, upserts as DBSignature[]);
        queryClient.invalidateQueries({ queryKey: keys.signatures.all(ctx) });
        break;
      }
      case "saved_search": {
        if (upserts.length) await upsertMany(db.saved_searches, upserts as DBSavedSearch[]);
        queryClient.invalidateQueries({ queryKey: keys.savedSearches.all(ctx) });
        break;
      }
    }
  }
}

// ── Full sync cycle ───────────────────────────────────────────────────────────

export async function runDeltaSync(
  accountId: string,
  ctx: KeyContext,
  queryClient: QueryClient,
  { maxPages = 10 }: { maxPages?: number } = {},
): Promise<void> {
  if (!db) return;

  // Load stored cursor
  const cursorRow = await db.sync_cursors.get(accountId);
  let cursor = cursorRow?.cursor ?? "0";
  let page = 0;

  while (page < maxPages) {
    let data: SyncResponse;
    try {
      const qs = `?since=${encodeURIComponent(cursor)}&limit=200`;
      data = await api.get<SyncResponse>(`/api/v1/sync${qs}`, {
        headers: { "X-Account-Id": accountId },
      });
    } catch {
      // Network error or API down — stop and let the drain handle retries
      break;
    }

    if (data.ops.length) {
      await applyOps(data.ops, ctx, queryClient);
    }

    cursor = data.next_cursor;
    await db.sync_cursors.put({ account_id: accountId, cursor, synced_at: new Date().toISOString() });
    page++;

    if (!data.has_more) break;
  }

  // After delta replay, drain the client op-log
  await drainOpLog(accountId);
}

// ── Background sync manager ───────────────────────────────────────────────────

let _syncTimer: ReturnType<typeof setInterval> | null = null;
let _syncAttached = false;

export function attachDeltaSync(
  accountId: string,
  ctx: KeyContext,
  queryClient: QueryClient,
  intervalMs = 30_000,
): () => void {
  if (_syncAttached || typeof window === "undefined") return () => {};
  _syncAttached = true;

  const sync = () => runDeltaSync(accountId, ctx, queryClient);
  window.addEventListener("online", sync);
  window.addEventListener("focus", sync);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") sync();
  });

  _syncTimer = setInterval(sync, intervalMs);

  // Initial sync on attach
  sync();

  return () => {
    window.removeEventListener("online", sync);
    window.removeEventListener("focus", sync);
    if (_syncTimer) clearInterval(_syncTimer);
    _syncAttached = false;
  };
}
