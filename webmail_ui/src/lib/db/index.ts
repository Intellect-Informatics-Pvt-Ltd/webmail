/**
 * PSense Mail — Dexie singleton.
 *
 * Import `db` wherever you need IndexedDB access.
 * The instance is created lazily on first import (SSR-safe: guards window check).
 */

import { PSenseMailDB } from "./schema";

let _db: PSenseMailDB | null = null;

export function getDb(): PSenseMailDB {
  if (_db) return _db;
  _db = new PSenseMailDB();
  return _db;
}

/** Convenience default export — use this in components and hooks. */
export const db = typeof window !== "undefined" ? new PSenseMailDB() : (null as unknown as PSenseMailDB);

export type { PSenseMailDB };
export * from "./schema";

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Upsert many records of a given Dexie table.
 * Uses bulkPut so each record is replaced if the primary key already exists.
 */
export async function upsertMany<T>(
  table: { bulkPut(items: T[]): Promise<unknown> },
  records: T[],
): Promise<void> {
  if (!records.length) return;
  await table.bulkPut(records);
}

/**
 * Soft-delete a record by marking its deleted_at field.
 * The record is kept in IDB for sync reconciliation.
 */
export async function softDelete<T extends { id: string; deleted_at?: string | null }>(
  table: { update(key: string, changes: Partial<T>): Promise<number> },
  id: string,
): Promise<void> {
  await table.update(id, { deleted_at: new Date().toISOString() } as Partial<T>);
}
