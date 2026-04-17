/**
 * PSense Mail — TanStack Query key factories.
 *
 * Centralises all query key construction so keys are:
 *   1. Type-safe (no ad-hoc string arrays scattered through the codebase).
 *   2. Hierarchical (invalidating `keys.messages.all(ctx)` also invalidates
 *      every `keys.messages.list(ctx, ...)` and `keys.messages.detail(ctx, ...)`).
 *   3. Tenant + account scoped — every key includes both IDs so multi-account
 *      users don't share caches.
 *
 * Naming convention:
 *   keys.<entity>.all(ctx)           — base key (invalidates all variants)
 *   keys.<entity>.list(ctx, filters) — list query
 *   keys.<entity>.detail(ctx, id)    — single-item query
 */

export interface KeyContext {
  tenantId: string;
  accountId: string;
}

// ── Messages ─────────────────────────────────────────────────────────────────

const messages = {
  all: (ctx: KeyContext) => [ctx.tenantId, ctx.accountId, "messages"] as const,
  list: (ctx: KeyContext, params: { folderId?: string; view?: string; cursor?: string }) =>
    [...messages.all(ctx), "list", params] as const,
  detail: (ctx: KeyContext, id: string) => [...messages.all(ctx), "detail", id] as const,
};

// ── Threads ───────────────────────────────────────────────────────────────────

const threads = {
  all: (ctx: KeyContext) => [ctx.tenantId, ctx.accountId, "threads"] as const,
  list: (ctx: KeyContext, params: { folderId?: string; cursor?: string }) =>
    [...threads.all(ctx), "list", params] as const,
  detail: (ctx: KeyContext, id: string) => [...threads.all(ctx), "detail", id] as const,
};

// ── Folders ───────────────────────────────────────────────────────────────────

const folders = {
  all: (ctx: KeyContext) => [ctx.tenantId, ctx.accountId, "folders"] as const,
  list: (ctx: KeyContext) => [...folders.all(ctx), "list"] as const,
  counts: (ctx: KeyContext) => [...folders.all(ctx), "counts"] as const,
};

// ── Categories ────────────────────────────────────────────────────────────────

const categories = {
  all: (ctx: KeyContext) => [ctx.tenantId, ctx.accountId, "categories"] as const,
  list: (ctx: KeyContext) => [...categories.all(ctx), "list"] as const,
};

// ── Rules ─────────────────────────────────────────────────────────────────────

const rules = {
  all: (ctx: KeyContext) => [ctx.tenantId, ctx.accountId, "rules"] as const,
  list: (ctx: KeyContext) => [...rules.all(ctx), "list"] as const,
};

// ── Templates ─────────────────────────────────────────────────────────────────

const templates = {
  all: (ctx: KeyContext) => [ctx.tenantId, ctx.accountId, "templates"] as const,
  list: (ctx: KeyContext) => [...templates.all(ctx), "list"] as const,
};

// ── Signatures ────────────────────────────────────────────────────────────────

const signatures = {
  all: (ctx: KeyContext) => [ctx.tenantId, ctx.accountId, "signatures"] as const,
  list: (ctx: KeyContext) => [...signatures.all(ctx), "list"] as const,
};

// ── Saved searches ────────────────────────────────────────────────────────────

const savedSearches = {
  all: (ctx: KeyContext) => [ctx.tenantId, ctx.accountId, "saved_searches"] as const,
  list: (ctx: KeyContext) => [...savedSearches.all(ctx), "list"] as const,
};

// ── Drafts ────────────────────────────────────────────────────────────────────

const drafts = {
  all: (ctx: KeyContext) => [ctx.tenantId, ctx.accountId, "drafts"] as const,
  list: (ctx: KeyContext) => [...drafts.all(ctx), "list"] as const,
  detail: (ctx: KeyContext, id: string) => [...drafts.all(ctx), "detail", id] as const,
};

// ── Preferences ───────────────────────────────────────────────────────────────

const preferences = {
  detail: (ctx: KeyContext) => [ctx.tenantId, ctx.accountId, "preferences"] as const,
};

// ── Search ────────────────────────────────────────────────────────────────────

const search = {
  results: (ctx: KeyContext, params: Record<string, unknown>) =>
    [ctx.tenantId, ctx.accountId, "search", params] as const,
  suggest: (ctx: KeyContext, q: string) =>
    [ctx.tenantId, ctx.accountId, "search", "suggest", q] as const,
};

// ── Feature flags ─────────────────────────────────────────────────────────────

const flags = {
  all: () => ["flags"] as const,
};

// ── Export ────────────────────────────────────────────────────────────────────

export const keys = {
  messages,
  threads,
  folders,
  categories,
  rules,
  templates,
  signatures,
  savedSearches,
  drafts,
  preferences,
  search,
  flags,
};
