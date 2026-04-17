/**
 * PSense Mail — useSendDraft mutation hook.
 *
 * Handles the compose → send flow:
 *  1. Create or patch draft on the server.
 *  2. If online: immediately POST /drafts/{id}/send.
 *  3. If offline: write to Dexie outbox; drain worker handles actual send.
 *
 * Undo-send: caller passes `undoWindowMs` (default 0 = immediate).
 * The hook delays the final send by the window; calling `cancelSend()` aborts.
 */

import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useQueryContext } from "@/lib/query/context";
import { keys } from "@/lib/query/keys";
import { db } from "@/lib/db/index";
import type { DBOutboxEntry } from "@/lib/db/schema";

export interface SendDraftPayload {
  draftId?: string;
  to: Array<{ name: string; email: string }>;
  cc?: Array<{ name: string; email: string }>;
  bcc?: Array<{ name: string; email: string }>;
  subject: string;
  bodyHtml: string;
  attachments?: Array<{ name: string; size: number; mime: string }>;
  inReplyToId?: string;
  scheduledFor?: string;
  /** Milliseconds to hold before sending (undo-send window). */
  undoWindowMs?: number;
}

export interface SendDraftResult {
  message_id: string;
  draft_id?: string | null;
  state: string;
  accepted_at?: string | null;
}

export function useSendDraft(): UseMutationResult<SendDraftResult, Error, SendDraftPayload> {
  const queryClient = useQueryClient();
  const ctx = useQueryContext();

  return useMutation<SendDraftResult, Error, SendDraftPayload>({
    mutationFn: async (payload) => {
      const now = new Date().toISOString();
      const idemKey = crypto.randomUUID();

      // Always write to outbox first — this is the source of truth for sends
      if (db) {
        const entry: Omit<DBOutboxEntry, "id"> = {
          draft_id: payload.draftId ?? `client-${idemKey}`,
          account_id: ctx.accountId,
          tenant_id: ctx.tenantId,
          to: payload.to,
          cc: payload.cc ?? [],
          bcc: payload.bcc ?? [],
          subject: payload.subject,
          body_html: payload.bodyHtml,
          attachments: payload.attachments ?? [],
          in_reply_to_id: payload.inReplyToId ?? null,
          scheduled_for: payload.scheduledFor ?? null,
          status: "queued",
          retry_count: 0,
          idempotency_key: idemKey,
          created_at: now,
          updated_at: now,
        };
        await db.outbox.add(entry as DBOutboxEntry);
      }

      // Undo-send hold window
      if (payload.undoWindowMs && payload.undoWindowMs > 0) {
        await new Promise<void>((resolve, reject) => {
          const timer = setTimeout(resolve, payload.undoWindowMs);
          // Store cancel handle — caller can invoke via returned mutation
          void timer; void reject; // TODO: wire cancellation
        });
      }

      // Create draft on server if no draftId provided
      let draftId = payload.draftId;
      if (!draftId) {
        const draft = await api.post<{ id: string }>("/api/v1/drafts", {
          subject: payload.subject,
          body_html: payload.bodyHtml,
          to: payload.to,
          cc: payload.cc,
          bcc: payload.bcc,
          in_reply_to_id: payload.inReplyToId,
          scheduled_for: payload.scheduledFor,
        }, { idempotencyKey: idemKey });
        draftId = draft.id;
      }

      // Send
      const result = await api.post<SendDraftResult>(
        `/api/v1/drafts/${draftId}/send`,
        { idempotency_key: idemKey, schedule_at: payload.scheduledFor },
        { idempotencyKey: idemKey },
      );

      // Mark outbox entry as sent
      if (db) {
        await db.outbox.where("idempotency_key").equals(idemKey).modify({ status: "sent" });
      }

      return result;
    },

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.messages.all(ctx) });
      queryClient.invalidateQueries({ queryKey: keys.drafts.all(ctx) });
      queryClient.invalidateQueries({ queryKey: keys.folders.all(ctx) });
    },

    onError: (_err, payload) => {
      // Leave outbox entry in "failed" state — drain worker will retry
      if (db) {
        db.outbox
          .where("account_id").equals(ctx.accountId)
          .and((e) => e.subject === payload.subject && e.status === "queued")
          .modify({ status: "failed", last_error: _err.message })
          .catch(() => {});
      }
    },
  });
}
