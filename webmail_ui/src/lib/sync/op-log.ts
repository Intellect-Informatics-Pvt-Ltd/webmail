/**
 * PSense Mail — Client op-log drain worker (Tier 3 offline).
 *
 * Drains the Dexie `op_log` table by replaying pending mutations against
 * the API. This ensures that flag/archive/move/snooze/categorize actions
 * made offline are durably replicated to the server on reconnect.
 *
 * Drain order: oldest-first per entity (FIFO).
 * On 409 ConcurrencyError: marks entry as `conflict` → surfaces conflict card.
 * On 4xx non-retryable: marks entry as `failed` → no more retries.
 * On 5xx / network error: increments retry_count with back-off.
 */

import { api } from "@/lib/api/client";
import { db } from "@/lib/db/index";

const MAX_RETRIES = 5;
const BACKOFF_BASE_MS = 1_000;

export type ConflictHandler = (entry: {
  entity: string;
  entity_id: string;
  action: string;
  serverPayload: unknown;
}) => void;

let _draining = false;
let _conflictHandler: ConflictHandler | null = null;

export function setConflictHandler(handler: ConflictHandler): void {
  _conflictHandler = handler;
}

export async function drainOpLog(accountId: string): Promise<void> {
  if (_draining || !db) return;
  _draining = true;

  try {
    const pending = await db.op_log
      .where("account_id").equals(accountId)
      .and((e) => e.status === "pending")
      .sortBy("created_at");

    for (const entry of pending) {
      if (!entry.id) continue;

      if ((entry.retry_count ?? 0) >= MAX_RETRIES) {
        await db.op_log.update(entry.id, { status: "failed" });
        continue;
      }

      if (entry.retry_count > 0) {
        await new Promise<void>((r) => setTimeout(r, Math.min(BACKOFF_BASE_MS * 2 ** (entry.retry_count - 1), 30_000)));
      }

      try {
        // All client op-log entries map to the bulk actions endpoint
        if (entry.entity === "message") {
          await api.post("/api/v1/messages/actions", {
            message_ids: entry.entity_id.split(","),
            action: entry.action,
            ...entry.payload,
          }, { idempotencyKey: entry.idempotency_key });
        }
        // Other entity types (folder rename, rule update, etc.) mapped here as they arrive

        await db.op_log.update(entry.id, { status: "sent", updated_at: new Date().toISOString() });
      } catch (err: unknown) {
        const apiErr = err as { status?: number; code?: string };
        const status = apiErr?.status ?? 0;
        const code = apiErr?.code ?? "";

        if (code === "CONCURRENCY_ERROR" || status === 409) {
          await db.op_log.update(entry.id, { status: "conflict", last_error: String(err) });
          _conflictHandler?.({
            entity: entry.entity,
            entity_id: entry.entity_id,
            action: entry.action,
            serverPayload: null,
          });
        } else if (status >= 400 && status < 500) {
          // Non-retryable 4xx (validation, not-found) — fail immediately
          await db.op_log.update(entry.id, {
            status: "failed",
            last_error: String(err),
            updated_at: new Date().toISOString(),
          });
        } else {
          // Retryable
          await db.op_log.update(entry.id, {
            retry_count: (entry.retry_count ?? 0) + 1,
            last_error: String(err),
            updated_at: new Date().toISOString(),
          });
        }
      }
    }
  } finally {
    _draining = false;
  }
}

let _timer: ReturnType<typeof setInterval> | null = null;
let _attached = false;

export function attachOpLogDrainer(accountId: string): () => void {
  if (_attached || typeof window === "undefined") return () => {};
  _attached = true;

  const drain = () => drainOpLog(accountId);
  window.addEventListener("online", drain);
  window.addEventListener("focus", drain);
  _timer = setInterval(drain, 60_000);
  drain();

  return () => {
    window.removeEventListener("online", drain);
    window.removeEventListener("focus", drain);
    if (_timer) clearInterval(_timer);
    _attached = false;
  };
}

/** Returns count of pending + failed op-log entries (for UI indicator). */
export async function opLogIssueCount(accountId: string): Promise<number> {
  if (!db) return 0;
  return db.op_log
    .where("account_id").equals(accountId)
    .and((e) => e.status === "pending" || e.status === "failed" || e.status === "conflict")
    .count();
}
