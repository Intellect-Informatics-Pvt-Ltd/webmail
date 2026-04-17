/**
 * PSense Mail — Outbox drain worker (Tier 2 offline).
 *
 * Drains the Dexie `outbox` table by sending queued drafts to the API.
 *
 * Trigger events:
 *   - `online` browser event
 *   - `visibilitychange` to visible
 *   - `focus`
 *   - Timer: every 60 s while tab is focused
 *
 * Retry policy: exponential back-off capped at 30 s, up to 5 attempts.
 * After 5 failures the entry is marked `failed` and surfaced in the UI.
 */

import { api } from "@/lib/api/client";
import { db } from "@/lib/db/index";

const MAX_RETRIES = 5;
const BACKOFF_BASE_MS = 2_000;
const TIMER_INTERVAL_MS = 60_000;

let _draining = false;
let _timer: ReturnType<typeof setInterval> | null = null;
let _attached = false;

async function _delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function drainOutbox(accountId: string): Promise<void> {
  if (_draining || !db) return;
  _draining = true;

  try {
    const entries = await db.outbox
      .where("account_id").equals(accountId)
      .and((e) => e.status === "queued" || e.status === "pending")
      .sortBy("created_at");

    for (const entry of entries) {
      if (!entry.id) continue;

      // Exponential back-off between retries
      if (entry.retry_count > 0) {
        await _delay(Math.min(BACKOFF_BASE_MS * 2 ** (entry.retry_count - 1), 30_000));
      }

      try {
        await db.outbox.update(entry.id, { status: "sending", updated_at: new Date().toISOString() });

        // Create draft then send (or re-send an existing draft)
        let draftId = entry.draft_id.startsWith("client-") ? undefined : entry.draft_id;

        if (!draftId) {
          const draft = await api.post<{ id: string }>("/api/v1/drafts", {
            subject: entry.subject,
            body_html: entry.body_html,
            to: entry.to,
            cc: entry.cc,
            bcc: entry.bcc,
            in_reply_to_id: entry.in_reply_to_id,
            scheduled_for: entry.scheduled_for,
          }, { idempotencyKey: entry.idempotency_key });
          draftId = draft.id;
          await db.outbox.update(entry.id, { draft_id: draftId });
        }

        await api.post(`/api/v1/drafts/${draftId}/send`, {
          idempotency_key: entry.idempotency_key,
          schedule_at: entry.scheduled_for,
        }, { idempotencyKey: entry.idempotency_key });

        await db.outbox.update(entry.id, { status: "sent", updated_at: new Date().toISOString() });
      } catch (err) {
        const count = (entry.retry_count ?? 0) + 1;
        const errMsg = err instanceof Error ? err.message : String(err);
        const newStatus = count >= MAX_RETRIES ? "failed" : "queued";
        await db.outbox.update(entry.id, {
          status: newStatus,
          retry_count: count,
          last_error: errMsg,
          updated_at: new Date().toISOString(),
        });
      }
    }
  } finally {
    _draining = false;
  }
}

export function attachOutboxDrainer(accountId: string): () => void {
  if (_attached || typeof window === "undefined") return () => {};
  _attached = true;

  const drain = () => drainOutbox(accountId);

  window.addEventListener("online", drain);
  window.addEventListener("focus", drain);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") drain();
  });

  _timer = setInterval(drain, TIMER_INTERVAL_MS);

  // Initial drain on attach
  drain();

  return () => {
    window.removeEventListener("online", drain);
    window.removeEventListener("focus", drain);
    if (_timer) clearInterval(_timer);
    _attached = false;
  };
}

/** Returns the count of pending outbox entries for the given account. */
export async function outboxPendingCount(accountId: string): Promise<number> {
  if (!db) return 0;
  return db.outbox
    .where("account_id").equals(accountId)
    .and((e) => e.status === "queued" || e.status === "pending" || e.status === "failed")
    .count();
}
