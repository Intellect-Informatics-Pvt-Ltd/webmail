/**
 * PSense Mail — useFolders query hook.
 */

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useQueryContext } from "@/lib/query/context";
import { keys } from "@/lib/query/keys";

export interface FolderSummary {
  id: string;
  name: string;
  kind: string;
  system: boolean;
  parent_id?: string | null;
  sort_order: number;
  icon?: string | null;
  unread_count: number;
  total_count: number;
  version?: number;
}

export function useFolders(options: { enabled?: boolean } = {}): UseQueryResult<FolderSummary[]> {
  const ctx = useQueryContext();

  return useQuery({
    queryKey: keys.folders.list(ctx),
    queryFn: () => api.get<FolderSummary[]>(`/api/v1/folders`),
    enabled: options.enabled ?? true,
    staleTime: 60 * 1000,
    meta: { persistable: true },
  });
}
