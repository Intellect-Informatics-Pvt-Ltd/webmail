/**
 * PSense Mail — useMessageAction mutation factory.
 *
 * Provides a single hook for ALL bulk message mutations (archive, delete,
 * move, flag, read, snooze, categorize, etc.).
 *
 * Features:
 *  - Optimistic update: patches the Query cache immediately.
 *  - Op-log append: writes to Dexie op_log for offline durability.
 *  - Rollback: on API error, reverses the optimistic patch.
 *  - Idempotency-Key: auto-generated per invocation.
 *  - If-Match: passes expectedVersion for optimistic concurrency.
 *  - Cache invalidation: invalidates the messages list after success.
 */

import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useQueryContext } from "@/lib/query/context";
import { keys } from "@/lib/query/keys";
import { db } from "@/lib/db/index";
import type { DBOpLogEntry } from "@/lib/db/schema";

// ── Types ─────────────────────────────────────────────────────────────────────

export type MessageActionType =
  | "archive"
  | "delete"
  | "restore"
  | "move"
  | "mark_read"
  | "mark_unread"
  | "flag"
  | "unflag"
  | "pin"
  | "unpin"
  | "snooze"
  | "unsnooze"
  | "categorize"
  | "uncategorize";

export interface MessageActionPayload {
  message_ids: string[];
  action: MessageActionType;
  destination_folder_id?: string;
  category_ids?: string[];
  snooze_until?: string;
  expected_version?: number;
}

export interface BulkActionResult {
  succeeded_ids: string[];
  failed: Record<string, string>;
  correlation_id?: string | null;
}

// ── Optimistic patch logic ────────────────────────────────────────────────────

function computeOptimisticPatch(
  action: MessageActionType,
  payload: MessageActionPayload,
): Record<string, unknown> {
  switch (action) {
    case "archive": return { folder_id: "archive" };
    case "delete": return { folder_id: "deleted" };
    case "restore": return { folder_id: "inbox" };
    case "mark_read": return { is_read: true };
    case "mark_unread": return { is_read: false };
    case "flag": return { is_flagged: true };
    case "unflag": return { is_flagged: false };
    case "pin": return { is_pinned: true };
    case "unpin": return { is_pinned: false };
    case "snooze": return { folder_id: "snoozed", snoozed_until: payload.snooze_until };
    case "unsnooze": return { folder_id: "inbox", snoozed_until: null };
    case "move": return { folder_id: payload.destination_folder_id };
    case "categorize": return {}; // complex — handled per message in the list
    case "uncategorize": return {};
    default: return {};
  }
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useMessageAction(): UseMutationResult<BulkActionResult, Error, MessageActionPayload> {
  const queryClient = useQueryClient();
  const ctx = useQueryContext();

  return useMutation<BulkActionResult, Error, MessageActionPayload>({
    mutationFn: async (payload) => {
      const idemKey = crypto.randomUUID();
      return api.post<BulkActionResult>("/api/v1/messages/actions", payload, {
        idempotencyKey: idemKey,
        expectedVersion: payload.expected_version,
      });
    },

    onMutate: async (payload) => {
      // Cancel in-flight queries for the affected messages
      await queryClient.cancelQueries({ queryKey: keys.messages.all(ctx) });

      const patch = computeOptimisticPatch(payload.action, payload);
      const now = new Date().toISOString();
      const idemKey = crypto.randomUUID();

      // Optimistically patch each message in the IDB cache
      if (db) {
        for (const id of payload.message_ids) {
          await db.messages.update(id, { ...patch, updated_at: now });
        }
      }

      // Append to client op-log for durability if offline
      if (db) {
        const entry: Omit<DBOpLogEntry, "id"> = {
          account_id: ctx.accountId,
          tenant_id: ctx.tenantId,
          entity: "message",
          entity_id: payload.message_ids.join(","),
          action: payload.action,
          payload: payload as Record<string, unknown>,
          optimistic_patch: patch,
          idempotency_key: idemKey,
          status: "pending",
          retry_count: 0,
          created_at: now,
          updated_at: now,
        };
        await db.op_log.add(entry as DBOpLogEntry);
      }

      // Snapshot existing cache for rollback
      const prevData = queryClient.getQueriesData({ queryKey: keys.messages.all(ctx) });

      // Apply optimistic patch to Query cache
      queryClient.setQueriesData({ queryKey: keys.messages.all(ctx) }, (old: unknown) => {
        if (!old || typeof old !== "object") return old;
        const page = old as { items: Array<Record<string, unknown>> };
        return {
          ...page,
          items: page.items.map((msg) =>
            payload.message_ids.includes(msg.id as string)
              ? { ...msg, ...patch }
              : msg,
          ),
        };
      });

      return { prevData, idemKey };
    },

    onError: (_err, _payload, context) => {
      // Roll back optimistic update
      if (context?.prevData) {
        for (const [queryKey, data] of context.prevData) {
          queryClient.setQueryData(queryKey, data);
        }
      }
    },

    onSuccess: (_result, payload) => {
      // Mark op-log entries as sent
      if (db) {
        db.op_log.where("action").equals(payload.action).modify({ status: "sent" }).catch(() => {});
      }
    },

    onSettled: () => {
      // Always re-fetch to reconcile with server truth
      queryClient.invalidateQueries({ queryKey: keys.messages.all(ctx) });
      queryClient.invalidateQueries({ queryKey: keys.threads.all(ctx) });
      queryClient.invalidateQueries({ queryKey: keys.folders.all(ctx) });
    },
  });
}
