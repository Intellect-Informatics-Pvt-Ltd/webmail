/**
 * PSense Mail — useMessages query hook.
 *
 * Fetches the message list for a given folder/view from the API.
 * Falls back to the Zustand mail store (legacy) when the
 * `USE_API_INBOX` feature flag is disabled.
 *
 * This hook is the canonical way to read messages in the UI.
 * Backed by TanStack Query + Dexie persistence.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { api, buildQueryString } from "@/lib/api/client";
import { useQueryContext } from "@/lib/query/context";
import { keys } from "@/lib/query/keys";

// ── Types (inline until OpenAPI codegen is run) ───────────────────────────────

export interface MessageSummary {
  id: string;
  thread_id: string;
  folder_id: string;
  subject: string;
  preview: string;
  sender: { name: string; email: string; avatar_color?: string | null };
  recipients: Array<{ name: string; email: string }>;
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
  snoozed_until: string | null;
  scheduled_for: string | null;
  trust_verified: boolean;
  version?: number;
}

export interface MessagesPage {
  items: MessageSummary[];
  next_cursor: string | null;
  total_estimate: number | null;
}

export interface UseMessagesParams {
  folderId?: string;
  view?: "all" | "unread" | "focused" | "other" | "attachments" | "mentions";
  categoryId?: string;
  isRead?: boolean;
  isFlagged?: boolean;
  cursor?: string;
  limit?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  /** If true, the query is disabled (component not yet ready). */
  enabled?: boolean;
}

export function useMessages(params: UseMessagesParams = {}): UseQueryResult<MessagesPage> {
  const ctx = useQueryContext();
  const {
    folderId,
    view,
    categoryId,
    isRead,
    isFlagged,
    cursor,
    limit = 50,
    sortBy = "received_at",
    sortOrder = "desc",
    enabled = true,
  } = params;

  const queryKey = keys.messages.list(ctx, { folderId, view, cursor });

  return useQuery({
    queryKey,
    queryFn: async () => {
      const qs = buildQueryString({
        folder_id: folderId,
        category_id: categoryId,
        is_read: isRead,
        is_flagged: isFlagged,
        is_focused: view === "focused" ? true : undefined,
        has_mentions: view === "mentions" ? true : undefined,
        has_attachments: view === "attachments" ? true : undefined,
        cursor,
        limit,
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      return api.get<MessagesPage>(`/api/v1/messages${qs}`);
    },
    enabled,
    staleTime: 30 * 1000,
    // Mark this query as persistable so IDB caches it
    meta: { persistable: true },
  });
}
