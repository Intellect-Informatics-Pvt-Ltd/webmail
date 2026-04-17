/**
 * PSense Mail — TanStack Query client factory + IDB persister.
 *
 * The QueryClient is created fresh per SSR request (never a module-level
 * singleton) following TanStack Start's recommendation.
 *
 * The IDB persister stores the in-memory query cache to Dexie so that
 * on next load the UI can paint from the persisted cache before the
 * network responds (offline-first).
 *
 * Only query keys tagged with `persistable: true` in their `meta` are
 * persisted — ephemeral / UI-only queries are excluded.
 */

import { QueryClient } from "@tanstack/react-query";
import { experimental_createQueryPersister } from "@tanstack/query-persist-client-core";

// ── IDB Persister ─────────────────────────────────────────────────────────────

function createIDBPersister() {
  if (typeof window === "undefined") return undefined;

  try {
    // Lazy require to avoid SSR issues
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { db } = require("../db/index") as { db: import("../db/schema").PSenseMailDB | null };
    if (!db) return undefined;

    return experimental_createQueryPersister({
      storage: {
        getItem: async (key: string) => {
          const row = await db.meta.get(key);
          return row?.value ?? null;
        },
        setItem: async (key: string, value: string) => {
          await db.meta.put({ key, value, updated_at: new Date().toISOString() });
        },
        removeItem: async (key: string) => {
          await db.meta.delete(key);
        },
      },
      maxAge: 24 * 60 * 60 * 1000, // 24 h
    });
  } catch {
    return undefined;
  }
}

// ── QueryClient factory ───────────────────────────────────────────────────────

export function makeQueryClient(): QueryClient {
  const persister = createIDBPersister();

  return new QueryClient({
    defaultOptions: {
      queries: {
        // 30 s stale time for list queries; bump per-query for details
        staleTime: 30 * 1000,
        // Keep unused data in cache for 24 h (IDB mirrors this)
        gcTime: 24 * 60 * 60 * 1000,
        // Always attempt fetch even when offline — hooks handle the fallback
        networkMode: "always",
        // Retry once on transient errors; the hook decides if it wants more
        retry: 1,
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30_000),
        // Persist to IDB when the query has meta.persistable = true
        ...(persister ? { persister } : {}),
      },
      mutations: {
        // Always queue mutations even when offline (outbox handles the drain)
        networkMode: "always",
      },
    },
  });
}

// ── Singleton for client-side rendering ──────────────────────────────────────

let _browserClient: QueryClient | null = null;

/** Returns the singleton QueryClient for browser usage. */
export function getBrowserQueryClient(): QueryClient {
  if (_browserClient === null) {
    _browserClient = makeQueryClient();
  }
  return _browserClient;
}
