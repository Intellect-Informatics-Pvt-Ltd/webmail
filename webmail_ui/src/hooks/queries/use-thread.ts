/**
 * PSense Mail — useThread query hook.
 *
 * Fetches a full thread (with all messages) from the API.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useQueryContext } from "@/lib/query/context";
import { keys } from "@/lib/query/keys";
import type { MessageSummary } from "./use-messages";

export interface MessageDetail extends MessageSummary {
  body_html?: string | null;
  body_text?: string | null;
  cc: Array<{ name: string; email: string }>;
  bcc: Array<{ name: string; email: string }>;
  attachments: Array<{ id: string; name: string; size: number; mime: string }>;
  in_reply_to_id?: string | null;
  delivery_state: string;
}

export interface ThreadDetail {
  id: string;
  subject: string;
  folder_id: string;
  participant_emails: string[];
  last_message_at: string | null;
  unread_count: number;
  total_count: number;
  has_attachments: boolean;
  is_flagged: boolean;
  messages: MessageDetail[];
}

export function useThread(
  threadId: string | null,
  options: { enabled?: boolean } = {},
): UseQueryResult<ThreadDetail> {
  const ctx = useQueryContext();

  return useQuery({
    queryKey: keys.threads.detail(ctx, threadId ?? ""),
    queryFn: () => api.get<ThreadDetail>(`/api/v1/threads/${threadId}`),
    enabled: !!threadId && (options.enabled ?? true),
    staleTime: 2 * 60 * 1000, // 2 min for detail
    meta: { persistable: true },
  });
}
