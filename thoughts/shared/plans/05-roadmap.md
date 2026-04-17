# PSense Mail — Unified Roadmap

**Status**: Draft v1.0 — for review before implementation.
**Last updated**: 2026-04-17.
**Supersedes**: `01-brd.md`, `02-implementation-plan.md`, `03-design-system.md`, `04-backend-architecture.md`, `mail_backend_facade_spec.md` (all removed in Phase 0; still-relevant sections are folded into this document).

This document is the single source of truth for PSense Mail product requirements, architecture, and phased implementation. It is written to be consumed by both humans (review) and agents (execution).

---

## Table of contents

0. [Purpose and scope](#0-purpose-and-scope)
1. [Product snapshot](#1-product-snapshot)
2. [Current state — what is shipped, scaffolded, or stale](#2-current-state)
3. [Guiding principles](#3-guiding-principles)
4. [Scope matrix — in scope, pluggable, deferred](#4-scope-matrix)
5. [Target architecture](#5-target-architecture)
6. [Data model](#6-data-model)
7. [API contract](#7-api-contract)
8. [Client architecture](#8-client-architecture)
9. [Offline architecture](#9-offline-architecture)
10. [Security and rendering](#10-security-and-rendering)
11. [Design system](#11-design-system)
12. [Observability and operations](#12-observability-and-operations)
13. [Python backend hardening](#13-python-backend-hardening)
14. [Phased implementation plan](#14-phased-implementation-plan)
15. [Acceptance criteria per phase](#15-acceptance-criteria-per-phase)
16. [Risks and mitigations](#16-risks-and-mitigations)
17. [TODO backlog — deferred and pluggable-not-enabled](#17-todo-backlog)
18. [Python façade spec — preserved reference](#18-python-façade-spec)
19. [Glossary](#19-glossary)

---

## 0. Purpose and scope

PSense Mail is a production-grade, enterprise webmail workspace branded for PSense.ai. Mail is the wedge; Calendar, Contacts, Tasks, and an AI Copilot are planned extensions that share the same shell, tokens, and data spine.

This roadmap covers:

- v1.0 → v1.3 across both the React client (`webmail_ui/`) and the FastAPI backend (`runtime/mail_api/`).
- The transition from a 100 % client-side mock to a real backend, including full offline support.
- Security, observability, multi-tenancy, multi-account, and provider-integration groundwork that must be baked in up front to avoid painful later migrations.

---

## 1. Product snapshot

### 1.1 Vision

A webmail workspace that feels as fast and focused as the best modern clients (Superhuman, Hey, Outlook for Business), branded for PSense.ai, and designed to host Calendar, Contacts, Tasks, and AI Copilot as first-class citizens on the same shell.

### 1.2 Personas

| Persona | Needs |
|---|---|
| Knowledge worker (sales, CS, ops) | Triaging high-volume inbox, keyboard nav, snooze, templates, signatures |
| Team lead / manager | Categorization, rules, focused inbox, mentions, OOO |
| Executive assistant | Multi-account access, scheduled send, delegation |
| IT admin | SSO (KeyCloak/OIDC), audit logs, retention, DLP-lite, tenant settings |

### 1.3 Non-goals for the v1 series

- Mobile native apps (responsive web only; native revisited after v1 metrics).
- End-to-end encrypted mail (S/MIME, PGP) — deferred, see §17.
- Full eDiscovery / legal hold / retention-lock — deferred, see §17.
- `.pst` import — deferred, see §17.

---

## 2. Current state

### 2.1 Client (`webmail_ui/`)

**Shipped:**
- Three-pane mail UI (rail / sidebar / list + reading pane) with all system folders plus custom folders, categories, favorites.
- Threaded conversations, attachments strip, multi-select, bulk actions, view tabs.
- Compose window with Tiptap, floating / full-screen / minimized modes, autosave, keyboard shortcuts.
- Rules center, templates manager, signatures settings route, mail settings route.
- Command palette (`⌘K`) and shortcuts modal (`?`).
- Light/dark themes, three density modes, reading-pane placement, toast notifications with undo.
- Calendar (day/week/month) and Contacts routes **exist** (AGENTS.md is stale — see §14.0).

**Not wired:**
- Zero network calls (`rg "fetch\(|useQuery|axios"` returns no matches under `src/`).
- `@tanstack/react-query` is installed but never mounted.
- No offline, no service worker, no IndexedDB.
- `ReadingPane` renders untrusted `bodyHtml` directly; no sanitization or iframe sandbox.
- No central keyboard-shortcut registry; shortcuts are duplicated across components.

### 2.2 Backend (`runtime/mail_api/`)

**Scaffolded:**
- FastAPI application factory with CORS, correlation, auth, and error middlewares (`app/main.py`).
- Façade services for mail, compose, search, attachments, rules, templates, signatures, categories, preferences, saved searches, admin.
- Adapter registry with pluggable transport (`mailpit | gmail | memory`), file storage (`nas | s3 | azure_blob | gcs`), search (`mongo | memory`), and database (`mongo | memory`).
- Workers for scheduled send, snooze wake-up, retries, inbound polling — in-process via `WorkerManager`.
- KeyCloak OIDC auth wired in config (disabled by default for dev).
- Tests under `runtime/mail_api/tests/` for facades and basic API.

**Gaps:**
- No `/v1` version prefix.
- Idempotency, optimistic concurrency (`expected_version`), and audit logging are specified but must be verified and hardened across all mutating endpoints.
- Workers are in-process — no horizontal scaling, no at-least-once guarantees, no DLQ.
- No OpenTelemetry, no `/metrics`, no rate limits, no GDPR export endpoints.
- No tenant_id / account_id on any model (multi-tenant and multi-account must be baked in early).
- No delta-sync endpoint.

### 2.3 Documentation drift

`AGENTS.md`, `02-implementation-plan.md`, and `04-backend-architecture.md` are out of sync with the code (Calendar/Contacts placeholders, signatures UI status) and contradict each other on the chosen backend (Lovable Cloud + Postgres + RLS vs. the actual FastAPI + MongoDB).

Phase 0 reconciles this into a single document (this one).

---

## 3. Guiding principles

1. **Offline-aware from day one.** Every read goes through a cache that can serve from IndexedDB; every write goes through a queue that tolerates disconnection. The "online" path is just "offline" with a drained queue.
2. **Tenant and account scoping from day one.** Every row is scoped to `tenant_id`, `account_id`, and `user_id`. Retrofitting this later is an order of magnitude more work than adding it now.
3. **Idempotency and monotonic versioning on every mutation.** Every mutating request accepts `Idempotency-Key` and `If-Match` (expected version). Replay-safe is the default.
4. **Adapters over branching.** Provider-specific or environment-specific behavior goes behind a protocol (transport, storage, search, preview, AV, push, notifications). Services and UI never reference concrete adapters.
5. **Untrusted content is rendered in a sandbox.** Remote HTML, inline scripts, and third-party assets never touch the top-level document.
6. **TypeScript and Python share a contract.** The server's OpenAPI spec is the single source of truth; the client regenerates types as part of the build.
7. **Semantic tokens only.** No hardcoded colors, no one-off pixel values, no custom fonts without explicit approval.
8. **Instrument before you optimize.** Every SLI (TTI, list FPS, send success rate, search p95) is emitted as metrics before performance work begins.

---

## 4. Scope matrix

Grades: **G** fully in scope (standard build); **Y** in scope but non-trivial; **O** in scope via pluggable adapter with default disabled; **R** deferred to TODO (§17).

| Area | Grade | Notes |
|---|---|---|
| Client foundation (IDB, Query, SDK, shortcut registry) | G | Phase 1 |
| Multi-tenant + multi-account data model | G | Phase 1 |
| API cutover + outbox + optimistic updates + idempotency | G | Phase 2 |
| Offline Tier 1 (read) | Y | Phase 3 |
| Offline Tier 2 (compose outbox) | Y | Phase 3 |
| Offline Tier 3 (action op-log) | Y | Phase 3 |
| Offline Tier 4 (delta sync + conflict resolution) | Y | Phase 3 |
| HTML rendering safety (DOMPurify + sandboxed iframe + remote-image block) | G | Phase 4 |
| First-time / external sender banners | G | Phase 4 |
| SPF/DKIM/DMARC display | Y | Phase 4 (provider-dependent) |
| Threading (RFC 2822) | G | Phase 4 |
| Undo-send + scheduled-send cancellation | G | Phase 4 |
| Attachment chunked/resumable upload | Y | Phase 4 |
| Inline image (`cid:`) handling | G | Phase 4 |
| Antivirus scan adapter | O | Phase 4 scaffold, ClamAV enablement TODO |
| Office/PDF preview adapter | O | Phase 4 scaffold, PDF-only default, Office enablement TODO |
| Web push (VAPID) adapter | O | Phase 4 scaffold, enablement TODO |
| SSO (OIDC via KeyCloak) | Y | Phase 4 |
| Audit log | G | Phase 4 |
| i18n extraction | G | Phase 4 |
| RTL layout audit | Y | Phase 4 or Phase 5 |
| `.eml` import/export, `.mbox` import, Print/Save-as-PDF | G | Phase 4 |
| Saved searches | G | Phase 4 |
| External worker queue (ARQ + Redis) | G | Phase 5 |
| OpenTelemetry + `/metrics` | G | Phase 5 |
| Rate limits + abuse | G | Phase 5 |
| Feature flags | G | Phase 5 |
| GDPR export/delete | G | Phase 5 |
| Microsoft Graph provider | Y | Phase 6 |
| S/MIME, PGP | **R** | §17 |
| Legal hold / eDiscovery | **R** | §17 |
| `.pst` import | **R** | §17 |
| Data residency (multi-region) | **R** | §17 (infra, not code) |

---

## 5. Target architecture

### 5.1 Stack

| Layer | Choice | Rationale |
|---|---|---|
| Client routing | TanStack Start v1 (file-based) | Already in use, SSR-capable. |
| Client UI | React 19 + Tailwind v4 + shadcn/ui | Shipped. |
| Client state — server cache | **TanStack Query v5** | Mounts in Phase 1, becomes authoritative for server data in Phase 2. |
| Client state — UI only | Zustand v5 | Shrinks after Phase 2 to ephemeral UI only (selection, overlays, pane sizes). |
| Client persistence | **Dexie (IndexedDB)** | Replaces `localStorage` for mail data. Hosts TanStack Query persister, outbox, op-log, attachment blobs. |
| Client offline | Workbox service worker | Shell + asset cache; push registration later. |
| Editor | Tiptap v3 | Shipped. |
| List virtualization | `@tanstack/react-virtual` | Shipped. |
| Forms + validation | react-hook-form + zod | Shipped pattern. |
| Client SDK | Generated via `openapi-typescript` | From `runtime/mail_api/` OpenAPI. |
| Backend framework | FastAPI (async) | Shipped. |
| Backend DB | **MongoDB** (Beanie ODM) | Shipped — supersedes the Postgres/RLS text in the old `04-backend-architecture.md`. |
| Backend file storage | NAS / S3 / Azure Blob / GCS adapters | Shipped. |
| Backend search | Mongo text index (default) with Meilisearch/OpenSearch adapter as escape hatch | Shipped protocol. |
| Backend transport | Mailpit (dev), Memory (tests), Gmail (scaffold), Microsoft Graph (Phase 6) | Shipped protocol. |
| Worker queue | **ARQ** (Redis) | Phase 5 replaces in-process `WorkerManager`. |
| Auth | **KeyCloak (OIDC)** | Config already present; enabled in Phase 4. |
| Observability | OpenTelemetry traces + metrics, Prometheus `/metrics`, structured logs, Sentry (client + server) | Phase 5. |
| Feature flags | Mongo collection + cached hook (lightweight) | Phase 5. |

### 5.2 Topology

```
┌──────────────────────────┐        ┌──────────────────────────────┐
│  Browser (React client)  │        │  FastAPI (runtime/mail_api)  │
│                          │        │                              │
│  TanStack Query cache ───┼─HTTPS─▶│  Routers  ──▶  Facades       │
│         │                │        │     │             │          │
│         ▼                │        │     │             ▼          │
│  Dexie (IDB)             │        │     │        Adapters        │
│  ├─ entity cache         │        │     │        (transport,     │
│  ├─ outbox (sends)       │        │     │         storage,       │
│  ├─ op-log (actions)     │        │     │         search,        │
│  ├─ attachment blobs     │        │     │         inbound)       │
│  └─ settings             │        │     ▼             ▼          │
│                          │        │   MongoDB      File stores   │
│  Service worker (SW)     │        │   (Beanie)     (NAS/S3/...)  │
│  ├─ shell precache       │        │                              │
│  ├─ runtime cache        │        │  ARQ workers (Phase 5)       │
│  ├─ push (Phase 4)       │        │  ├─ scheduled send           │
│  └─ background sync      │        │  ├─ snooze wake              │
│                          │        │  ├─ retry / DLQ              │
│  Zustand (UI only)       │        │  ├─ inbound poll / webhook   │
│                          │        │  └─ rule executor            │
└──────────────────────────┘        └──────────────┬───────────────┘
                                                   │
                                                   ▼
                                         KeyCloak (OIDC)
                                         Mailpit / Gmail /
                                         Microsoft Graph
                                         Redis (queue + rate limit)
                                         ClamAV (optional)
                                         Gotenberg (optional preview)
                                         Push service (VAPID, optional)
```

### 5.3 Data flow — online

1. Component calls a typed hook (`useMessages(folderId)`).
2. TanStack Query checks the in-memory cache; if miss, reads from the Dexie persister for an instant paint; then fires the HTTP request.
3. Server response hydrates the Query cache; the persister mirror writes to Dexie with a write-through policy.
4. Mutations call typed hooks (`useArchive()`), which apply an optimistic patch to the cache, enqueue in the op-log for durability, call the API with `Idempotency-Key` and `If-Match`, and reconcile on response.

### 5.4 Data flow — offline

1. On startup, Query cache is seeded from Dexie; UI paints from last-known data.
2. Reads that miss the cache (and cannot fall back to IDB) surface an "unavailable offline" empty state with a CTA to download.
3. Mutations still go through the same hooks. Because `networkMode: 'always'`, they apply optimistic patches and append to the op-log. The drain worker retries on `online` / `focus` / `visibilitychange` events.
4. On reconnect, the client first pulls `/v1/sync?since=<cursor>` to catch up with server changes, then drains the op-log top-down; conflicts are surfaced to the user (see §9.4).

---

## 6. Data model

All schemas are MongoDB via Beanie. Every collection has `tenant_id`, `account_id`, `user_id`, `created_at`, `updated_at`, `version` (monotonic int), and (for soft-deletable entities) `deleted_at`.

### 6.1 Tenancy and identity

| Concept | Meaning |
|---|---|
| `tenant` | An organization or workspace. Top-level isolation boundary. |
| `account` | A mail identity belonging to a user (e.g. `avery@psense.ai`). A user can have multiple accounts; `ownership` is enforced via `account_user` association. |
| `user` | An authenticated principal (KeyCloak subject). |
| `delegation` (future) | `account` → `user` access grant with role (e.g. `read`, `send_as`). Out of scope for v1 but the schema tolerates it. |

### 6.2 Collections

All enumerations live in `app/domain/enums.py` (already present). Schemas are shown as TypeScript-ish signatures for readability; actual Beanie models live in `app/adapters/db/*`.

```ts
Tenant {
  _id: ObjectId
  slug: string          // short identifier for URLs
  name: string
  created_at, updated_at
  version: int
}

User {
  _id: ObjectId
  tenant_id: ObjectId
  oidc_subject: string   // from KeyCloak
  email: string
  display_name: string
  avatar_url?: string
  created_at, updated_at
  version: int
}

Account {
  _id: ObjectId
  tenant_id: ObjectId
  owner_user_id: ObjectId
  address: string        // "avery@psense.ai"
  display_name: string
  provider: "mailpit" | "gmail" | "microsoft_graph" | "memory"
  provider_meta: { ... }  // refresh tokens live encrypted at rest
  is_primary: bool
  sync_cursor?: string    // provider delta cursor
  created_at, updated_at
  version: int
  deleted_at?: datetime
}

AccountUser {
  _id
  account_id, user_id
  role: "owner" | "delegate_read" | "delegate_send"
  created_at
}

Folder {
  _id
  tenant_id, account_id
  name
  kind: "inbox" | "focused" | "other" | "drafts" | "sent"
       | "archive" | "snoozed" | "flagged" | "deleted" | "junk" | "custom"
  parent_id?: ObjectId
  system: bool
  color?: string
  created_at, updated_at
  version, deleted_at?
}

Category {
  _id
  tenant_id, account_id
  name, color
  version, deleted_at?
}

Thread {
  _id
  tenant_id, account_id
  subject
  participant_emails: string[]
  message_ids: ObjectId[]
  last_received_at
  unread_count: int
  has_attachments: bool
  is_flagged: bool
  folder_id
  version, deleted_at?
}

Message {
  _id
  tenant_id, account_id
  thread_id, folder_id
  message_id_header: string    // RFC 2822 Message-ID
  in_reply_to_header?: string
  references_headers: string[]
  subject, preview, body_html, body_text
  sender: { name, email }
  recipients, cc, bcc          // arrays of { name, email }
  received_at
  is_read, is_flagged, is_pinned, has_attachments
  importance: "low" | "normal" | "high"
  category_ids: ObjectId[]
  snoozed_until?, scheduled_for?
  is_draft, is_focused, has_mentions
  trust_verified: bool
  authentication_results?: {
    spf: "pass"|"fail"|"neutral"|"softfail"|"none"
    dkim: ...
    dmarc: ...
  }
  external: bool               // outside tenant's domain
  first_time_sender: bool
  delivery_state: "draft"|"queued"|"sending"|"sent"|"failed_retryable"
                 |"failed_permanent"|"scheduled"|"cancelled"
  provider_ids: { ... }        // provider-specific opaque IDs
  version, deleted_at?
}

Attachment {
  _id
  tenant_id, account_id
  message_id
  name, size, mime
  storage_adapter: "nas"|"s3"|"azure_blob"|"gcs"
  storage_key: string
  checksum_sha256
  av_state: "unknown"|"clean"|"infected"|"skipped"
  preview_state: "none"|"ready"|"failed"
  preview_keys?: { ... }
  created_at
}

Rule {
  _id
  tenant_id, account_id
  name, enabled
  conditions: [...], actions: [...]
  version, deleted_at?
}

Template, Signature, SavedSearch — straightforward per-account CRUD.

UserPreferences {
  _id
  user_id, account_id
  density, reading_pane, conversation_view, focused_inbox,
  default_sort, preview_lines, theme, default_reply,
  notifications: { desktop, sound, only_focused, push_enabled, quiet_hours },
  out_of_office: { enabled, message, start?, end? },
  shortcuts_enabled: bool
  version
}

IdempotencyKey {
  _id
  tenant_id, account_id, user_id
  key: string
  route: string
  request_hash: string
  response_body: BSON            // cached response
  expires_at                     // TTL-indexed
}

OpLogEntry {                     // per-account change feed (Phase 3)
  _id
  tenant_id, account_id
  seq: int64 (monotonic)
  kind: "upsert"|"delete"
  entity: "message"|"thread"|"folder"|"category"|"rule"|...
  entity_id
  payload: BSON
  created_at
}

AuditLog {                       // Phase 4
  _id
  tenant_id, account_id, user_id
  action, subject_type, subject_id
  metadata, ip, user_agent
  created_at                     // TTL by retention policy
}

FeatureFlag {                    // Phase 5
  _id
  key, enabled: bool
  rollout: { strategy, percentage?, tenant_allowlist?, user_allowlist? }
}
```

### 6.3 Indexes (minimum)

- `messages`: `(tenant_id, account_id, folder_id, received_at desc)`, `(tenant_id, thread_id)`, `(tenant_id, account_id, is_read) where is_read=false`, text index on `(subject, preview, body_text, sender.email)`.
- `threads`: `(tenant_id, account_id, folder_id, last_received_at desc)`.
- `op_log`: `(tenant_id, account_id, seq)`.
- `idempotency_keys`: unique `(tenant_id, user_id, key)`, TTL on `expires_at`.
- `audit_log`: `(tenant_id, created_at desc)`, TTL on `created_at` per policy.
- Every collection: compound `(tenant_id, updated_at)` for delta sync.

### 6.4 Versioning, tombstones, idempotency

- **Version.** Every mutable document carries an integer `version`. Updates require `If-Match: <version>`; the server increments atomically on write and returns the new value. Conflicting updates raise `ConcurrencyError`.
- **Tombstones.** Deletes set `deleted_at` and increment `version`. Delta sync emits a `delete` op; hard delete runs via a retention worker after N days.
- **Idempotency.** Every mutating endpoint accepts `Idempotency-Key` in header. The backend stores the request hash and cached response for 24 h; replays within window return the cached response; conflicting bodies with the same key raise `409`.
- **Op-log (server side).** Every write appends an entry to `op_log` in the same session as the document write (`session.start_transaction` wrapping when on a replica set, or two-step with compensating delete on failure in standalone Mongo).

### 6.5 Migration from current seed

The existing `src/data/{messages,folders,categories,contacts,calendar-events}.ts` seed is migrated to a server-side seed (`app/seed/demo_data.py`, already scaffolded for memory backend). Phase 2 adds a `seed_mongo` path that runs on first boot when the `demo_seed` feature flag is enabled.

---

## 7. API contract

### 7.1 Base conventions

- **Prefix**: `/v1` on every router. Breaking changes rev to `/v2`.
- **Auth**: Bearer JWT from KeyCloak; dev mode allows a configurable `dev_user_id` (see `config/default.yaml`).
- **Correlation**: `X-Correlation-ID` in/out, logged on every line.
- **Idempotency**: `Idempotency-Key` required on every `POST` / `PATCH` / `DELETE` that isn't itself idempotent. Responses echo `X-Idempotency-Replay: true` when served from cache.
- **Optimistic concurrency**: `If-Match: <version>` on `PATCH`; `ETag: <version>` on responses.
- **Pagination**: cursor-based; `cursor`, `limit` params; responses include `next_cursor` and `prev_cursor`.
- **Error envelope** (see §7.5).
- **Tenant + account resolution**: `tenant_id` from the JWT claim; `account_id` from an `X-Account-Id` header (defaults to primary account for the user). All responses filter strictly on these.

### 7.2 Endpoints (grouped)

| Group | Endpoints |
|---|---|
| `mailbox` | `GET /v1/mailboxes/{account_id}/folders` |
| `threads` | `GET /v1/threads?folder_id=&cursor=&view=`, `GET /v1/threads/{id}` |
| `messages` | `GET /v1/messages/{id}`, `POST /v1/messages/actions` (bulk), `POST /v1/messages/{id}/read`, etc. |
| `drafts` | `POST /v1/drafts`, `PATCH /v1/drafts/{id}`, `POST /v1/drafts/{id}/send`, `POST /v1/drafts/{id}/cancel-send` |
| `attachments` | `POST /v1/attachments/init`, `PATCH /v1/attachments/{upload_id}/chunk`, `POST /v1/attachments/{upload_id}/finalize`, `GET /v1/attachments/{id}` |
| `search` | `POST /v1/search/messages`, `GET /v1/search/suggest?q=` |
| `rules` / `templates` / `signatures` / `categories` / `saved-searches` | Standard CRUD. |
| `preferences` | `GET /v1/preferences`, `PATCH /v1/preferences`. |
| `sync` | `GET /v1/sync?since=<cursor>&account_id=` (see §7.3). |
| `admin` | `GET /v1/admin/health`, `POST /v1/admin/seed`, `POST /v1/admin/replay-failed`. |
| `audit` | `GET /v1/audit?subject_type=&subject_id=` (admin only, Phase 4). |
| `gdpr` | `POST /v1/gdpr/export`, `DELETE /v1/gdpr/user/{id}` (Phase 5). |

### 7.3 Delta sync endpoint

```
GET /v1/sync?since=<opaque_cursor>&account_id=<id>&limit=500

200 OK
{
  "next_cursor": "...",
  "ops": [
    { "seq": 120341, "kind": "upsert", "entity": "message",
      "id": "...", "payload": { ... } },
    { "seq": 120342, "kind": "delete", "entity": "thread",
      "id": "...", "deleted_at": "..." }
  ],
  "has_more": true
}
```

- Cursors are opaque, monotonic, tenant-scoped.
- Clients persist the latest cursor per `account_id` in IDB.
- Entities returned are full current projections (so a client that missed N updates collapses them into one).
- Payloads are gzipped via standard content negotiation.

### 7.4 OpenAPI → TypeScript SDK pipeline

- Backend exposes `/openapi.json`.
- Client build step (`npm run gen:api`) runs `openapi-typescript` against `http://localhost:8000/openapi.json` (or a committed snapshot for CI) and writes `webmail_ui/src/lib/api/types.gen.ts`.
- A thin hand-written `src/lib/api/client.ts` wraps `fetch`, injects auth header, correlation ID, idempotency key, and handles the error envelope.
- The snapshot is committed; CI fails if regenerated output differs — guaranteeing client/server drift is caught at PR time.

### 7.5 Error model

```json
{
  "error": {
    "code": "validation_error",
    "message": "subject is required",
    "correlation_id": "018f...",
    "details": { "field": "subject" },
    "retryable": false
  }
}
```

Codes map to domain exceptions already defined in `runtime/mail_api/app/domain/errors.py`:

| HTTP | Code | Domain exception |
|---|---|---|
| 400 | `validation_error` | `ValidationError` |
| 401 | `unauthenticated` | (middleware) |
| 403 | `forbidden` / `policy_denied` | `PolicyDeniedError` |
| 404 | `not_found` | `NotFoundError` |
| 409 | `conflict` / `concurrency` | `ConflictError` / `ConcurrencyError` |
| 422 | `validation_error` | `ValidationError` |
| 429 | `rate_limited` | `RateLimitedError` |
| 502 | `provider_unavailable` | `ProviderUnavailableError` |
| 503 | `retryable_delivery` | `RetryableDeliveryError` |

---

## 8. Client architecture

### 8.1 Layered responsibilities

```
src/
├── lib/
│   ├── api/                # generated types + hand-rolled client
│   ├── db/                 # Dexie schema + helpers
│   ├── sync/               # delta replay, op-log drain, outbox drain
│   ├── query/              # QueryClient, persister, keys, helpers
│   ├── shortcuts/          # central registry + provider
│   ├── security/           # sanitizer, iframe mount helpers (Phase 4)
│   ├── i18n/               # message catalogs + formatter (Phase 4)
│   └── utils.ts
├── hooks/
│   ├── queries/            # useMessages, useThread, useFolders, ...
│   ├── mutations/          # useArchive, useMoveTo, useSendDraft, ...
│   └── ui/                 # use-mobile, use-shortcut, ...
├── stores/
│   └── ui-store.ts         # shrinks — ephemeral UI only after Phase 2
├── components/
│   ├── layout, mail, compose, calendar, contacts
│   ├── safety/             # RemoteImageBanner, SenderTrustBanner (Phase 4)
│   └── ui/
├── routes/ (unchanged structure)
├── types/                  # domain types (mirror of server, augmented)
└── styles.css
```

### 8.2 Storage stack (Dexie)

Schema lives at `src/lib/db/schema.ts`:

```ts
db.version(1).stores({
  messages:    '&id, tenant_id, account_id, folder_id, thread_id, received_at, version, deleted_at',
  threads:     '&id, tenant_id, account_id, folder_id, last_received_at, version',
  folders:     '&id, tenant_id, account_id, parent_id, version',
  categories:  '&id, tenant_id, account_id, version',
  rules:       '&id, tenant_id, account_id, version',
  templates:   '&id, tenant_id, account_id, version',
  signatures:  '&id, tenant_id, account_id, version',
  saved_searches: '&id, tenant_id, account_id, version',
  preferences: '&id, user_id',
  attachments_meta: '&id, message_id, version',
  attachments_blobs: '&id',              // Blob cached for offline
  outbox:      '++id, account_id, status, created_at',
  op_log:      '++id, account_id, status, created_at',
  sync_cursors: '&account_id',
  meta:        '&key',
});
```

Helpers expose strongly-typed CRUD and a unified `upsertMany(entity, records)` used by the delta replay.

### 8.3 TanStack Query conventions

- Keys: `[entity, tenantId, accountId, ...filters]`. A helper `keys.messages({accountId, folderId})` prevents ad-hoc key construction.
- Persistence: `persistQueryClient` with `createIDBPersister(db.meta, 'query-cache')` — only `queryKey` prefixes tagged `persistable` are persisted; UI-specific queries (e.g. list of currently selected IDs) are not.
- Stale / GC: list queries `staleTime: 30s`, `gcTime: 24h`. Detail queries `staleTime: 2m`.
- Mutations: all mutating hooks are created by a factory `createMutationHook({ endpoint, optimistic, invalidate })` that handles `Idempotency-Key`, `If-Match`, op-log append, and invalidation.
- Network mode: `networkMode: 'always'` so mutations always run (enabling offline queueing).

### 8.4 Zustand reduction

After Phase 2, `mail-store.ts` is deleted. `compose-store.ts` shrinks to "which draft is open" (one `openDraftId`; drafts live in IDB). `ui-store.ts` keeps selection, overlays, list view, sidebar widths, pane sizes.

### 8.5 Shortcut registry

- `src/lib/shortcuts/registry.ts` exposes `registerShortcut({ id, keys, scope, handler, description })`.
- `<ShortcutProvider>` at the root sets up a single global listener with scope stacking (`global` > `route` > `modal`).
- The `?` modal reads from the registry so shortcuts are always self-documenting.
- `useShortcut(id)` provides a declarative hook for per-component registration.

### 8.6 Error boundary / loader / empty-state taxonomy

- Every route has an `errorComponent` (via TanStack Router) that renders a localized `<ErrorState kind="...">` card.
- Every list surface uses `<EmptyState icon headline description cta?>`.
- Every async surface renders `<SkeletonRows count=...>` during first-load; subsequent loads show in-place refresh indicators.

---

## 9. Offline architecture

### 9.1 Tier 1 — Read-offline

- **Service worker** (`public/sw.js`, generated via `vite-plugin-pwa` in `injectManifest` mode): precaches the app shell, runtime-caches static assets with `StaleWhileRevalidate`, runtime-caches `GET /v1/*` with `NetworkFirst` falling back to IDB for list endpoints.
- **IDB hydration** happens before first render: `db.open()` → load persisted query cache → hydrate QueryClient.
- **Per-folder cache policy**:
  - Inbox and Focused: always cached; last 2 weeks of metadata + last 3 days of bodies.
  - Other system folders: metadata-only on-demand; bodies cached for opened threads.
  - Custom folders: metadata on visit; bodies on open.
- **Per-thread "Available offline"** action forces download of the full thread (all messages + attachments) into IDB with no TTL.

### 9.2 Tier 2 — Compose outbox

- A draft in compose is persisted to `outbox` table (not to `drafts` route cache) as soon as any field is edited.
- `useSendDraft` mutation sets `outbox.status = 'queued'` and returns to the UI immediately; the drain worker posts to `POST /v1/drafts/{id}/send`.
- Drain triggers: `online` event, `visibilitychange: visible`, `focus`, and a timer (60 s while online).
- On permanent failure (4xx non-retryable, or N retries for 5xx with backoff), status becomes `failed`; the UI surfaces an "Outbox" sidebar item with a retry/edit/delete affordance.
- Attachments in a queued draft are kept as `Blob`s in `attachments_blobs`; on drain they are uploaded via chunked-upload (`/v1/attachments/init` → chunks → finalize).

### 9.3 Tier 3 — Action op-log

- Every mutation is also appended to `op_log` with `status = 'pending'`.
- Optimistic UI change is applied locally in the Query cache **and** mirrored into Dexie, so the change survives a reload.
- Drain policy: FIFO per entity id; retries with exponential backoff capped at 30 s; permanent failures surface a per-entry toast and a "Sync issues" center.
- Conflicts (`409` from server): the op-log entry is marked `conflict`; the client fetches the current server version and prompts the user (auto-resolve simple flag races; ask for user intent on folder/delete conflicts).

### 9.4 Tier 4 — Delta sync + conflict resolution

- On startup and on every `online` event, the client calls `GET /v1/sync?since=<cursor>` in a loop until `has_more = false`.
- Applied ops overwrite Dexie + Query cache with server-authoritative state.
- **After** delta replay, the op-log is drained.
- Conflict policy:
  - **Read flags, flag/pin, category tags**: last-write-wins. Op-log retries until success.
  - **Move / archive / delete**: server authoritative; if server state differs from expected, surface a conflict card showing "you moved X to Y; meanwhile X was moved to Z. Keep server? Apply your change?".
  - **Sends**: idempotent via `Idempotency-Key`; replay is safe.
- **Watchdog**: if the op-log cannot drain for > 5 minutes while online, surface a persistent "Sync issue — N pending" toast with a "view" action.

### 9.5 Quotas, eviction, storage budget

- Target < 200 MB IDB per user on disk. Eviction worker drops:
  1. Non-flagged, non-pinned messages older than 30 days from non-Inbox folders.
  2. Attachment blobs for threads not opened in the last 14 days (metadata retained).
  3. Query cache entries older than 24 h.
- Navigator.storage.estimate() sampled hourly; if usage > 80 % of quota, aggressive eviction runs.
- "Available offline" threads are never evicted until explicitly removed.

---

## 10. Security and rendering

### 10.1 HTML body sanitization + sandboxed iframe

- Add `isomorphic-dompurify`.
- `MailBodyRenderer` mounts an iframe with `sandbox="allow-same-origin"` (no `allow-scripts`), pointed at a `srcdoc` containing sanitized HTML, a tight `<meta http-equiv="Content-Security-Policy">`, and a base stylesheet that inherits design tokens.
- Sanitizer config blocks: `<script>`, event handlers, `javascript:` URLs, `<meta http-equiv="refresh">`, embedded `<iframe>`, and `<object>`/`<embed>`.
- All outbound links get `rel="noopener noreferrer"` and open in a new tab; links whose display text differs substantially from the URL (punycode, host mismatch) get a confirmation interstitial.

### 10.2 Remote image / tracking pixel blocking

- By default, remote images are blocked; the renderer shows a banner "Images from <sender> are blocked — Show images" with a persistable per-sender trust memory.
- Tracking pixels (1×1 transparent, known tracker domains) remain blocked even after user opts in, unless a power-user toggle disables the allowlist.
- A proxy endpoint `GET /v1/proxy/image?src=` strips trackers and serves sanitized images when the user clicks "Show images" — avoids leaking IP/User-Agent to the sender.

### 10.3 Content Security Policy + sandbox attributes

- Production response headers include a strict `Content-Security-Policy` (no inline scripts in shell; inline-style allowed via nonce; fonts from `self`; connect to API origin only).
- The iframe `srcdoc` carries its own CSP that additionally blocks `script-src` entirely.

### 10.4 Sender trust UI

- `FirstTimeSenderBanner` shows when the user has never corresponded with `sender.email` before.
- `ExternalSenderBanner` shows when sender's domain ≠ any of the tenant's domains.
- `AuthResultsBadge` surfaces SPF / DKIM / DMARC pass/fail status extracted from `Authentication-Results` header (provider-dependent).
- Consolidated `SenderTrustBanner` renders the worst-severity issue only, with a "learn more" popover.

### 10.5 Pluggable adapters (default disabled)

- **`AntiVirusAdapter`**: protocol `scan(stream) -> {state, details}`. Default implementation `NoOpScanner` marks all attachments `skipped`. ClamAV adapter added as a sidecar in TODO (§17). Attachments with `av_state != 'clean'` require an explicit "download anyway" confirmation.
- **`PreviewAdapter`**: protocol `preview(attachment) -> {uri, kind}`. Default renders PDFs client-side via `pdfjs-dist`; Office-format enablement deferred (Gotenberg/LibreOffice headless).
- **`PushAdapter`**: protocol `subscribe(user) -> subscription`; `send(subscription, payload)`. VAPID keys configured; default implementation is a no-op until the push backend is deployed.

### 10.6 Undo-send + scheduled-send semantics

- **Undo-send window**: configurable (0 / 5 / 10 / 20 / 30 s). Client-side hold: when the user hits send, the mutation is enqueued but its `run_after` is `now + window`; an always-on "Undo" toast blocks navigation-away losing it. The server only sees the send after the window expires.
- **Scheduled send**: client requires a timezone; `scheduled_for` is stored in UTC. The scheduler worker (ARQ in Phase 5) picks up at minute granularity. Cancellation is `POST /v1/drafts/{id}/cancel-send` which flips `delivery_state` back to `draft`. Cancelling while the worker is mid-send returns `409`; UI offers "too late to cancel".

### 10.7 Threading specification (RFC 2822)

- Outbound messages carry a generated `Message-ID` (`<uuid@tenant-slug.psense.ai>`), `In-Reply-To` equal to the parent's `message_id_header`, and `References` equal to the parent's `References` concatenated with the parent's `Message-ID`.
- Inbound threading uses, in order: `In-Reply-To` → `References` last ID → provider's thread ID → subject-base (normalized: strip `Re:`, `Fwd:`, trim, lowercase) **only as a last resort**, never across different participant sets.
- Thread promotion: if an orphan message arrives whose `In-Reply-To` did not yet exist in the DB, it parks on an "orphan" index; when the parent arrives (or never), a reconciliation pass attaches it.

---

## 11. Design system

*(Unchanged from the prior `03-design-system.md` except where noted — folded here so this document is self-contained.)*

### 11.1 Brand identity

- **Product**: PSense Mail — parent brand PSense.ai.
- **Voice**: calm, focused, professional. Never playful.
- **Logo**: `src/assets/psense-logo.svg` — purple wordmark; sidebar header + command palette + mandatory "Powered by PSense" footer on every screen.

### 11.2 Color tokens

All colors are `oklch` in `webmail_ui/src/styles.css`, exposed as semantic CSS variables. **Never hardcode hex/rgb in components.**

- Core: `--background`, `--foreground`, `--card`, `--popover`, `--primary`, `--primary-foreground`, `--secondary`, `--muted`, `--muted-foreground`, `--accent`, `--destructive`, `--success`, `--warning`, `--info`, `--border`, `--input`, `--ring`.
- Sidebar/rail: `--sidebar*`, `--rail*`.
- Dark mode overrides every token in the `.dark` block.
- When adding a new semantic color, update `@theme inline`, `:root`, and `.dark` in a single edit.

### 11.3 Typography

| Role | Font stack | Size / weight |
|---|---|---|
| UI (default) | System sans | 14px / 400 |
| Headings | System sans | 16–24px / 600 |
| Code / mono | System mono | 13px / 400 |
| Email body (compose, reading) | System sans, larger line-height | 15px / 1.6 |

No custom web fonts without explicit approval.

### 11.4 Spacing and density

Three density modes (`compact` 36 px / `comfortable` 52 px / `spacious` 68 px) driven by `prefs.density`. Spacing scale follows Tailwind's 4 px base unit.

### 11.5 Layout

Same shell diagram as `03-design-system.md`: rail (56 px) — sidebar (240–280 px, resizable) — list (flex, min 320 px) — reading pane (resizable; right/bottom/off) — footer (32 px).

### 11.6 Component principles

- shadcn/ui primitives only — never roll custom focus traps or ARIA.
- Icons: `lucide-react` only. 16 px dense, 20 px elsewhere.
- Motion: `framer-motion` for compose open/close, command palette, toast. Subtle. No bouncy springs.
- Every list has an empty state; every async surface has a skeleton.

### 11.7 Accessibility

- Visible focus rings on every interactive element via `--ring`.
- Full keyboard (tab order matches visual; arrow + `j/k` in lists).
- ARIA via shadcn primitives; don't manually wire ARIA.
- Color contrast ≥ WCAG AA.
- `aria-label` on every icon-only button.
- Shortcut modal (`?`) lists every shortcut (from the registry — §8.5).
- Respect `prefers-reduced-motion`.

### 11.8 Theming rules

- One source of truth: `webmail_ui/src/styles.css` `:root` (light) and `.dark` (dark).
- No inline styles for color, spacing, typography.
- No Tailwind color utilities like `bg-purple-600`; use `bg-primary`, `bg-sidebar`, etc.

### 11.9 Don'ts

- No hardcoded colors.
- No custom fonts beyond system stack without approval.
- No MUI / Chakra / Mantine.
- No icon libraries besides lucide-react.
- No CSS-in-JS runtime libs.
- No bouncy / playful animations.

---

## 12. Observability and operations

### 12.1 Logs, metrics, traces

- **Logs**: structured JSON. Every line carries `correlation_id`, `tenant_id`, `user_id`, `account_id`, `route`. PII redaction middleware masks email addresses in body previews inside logs.
- **Metrics** (`/metrics` via `prometheus-fastapi-instrumentator`):
  - HTTP: request count, latency histograms, error rate per route.
  - Domain: `send_success_total`, `send_failed_total{reason}`, `snooze_wake_count`, `rule_match_count`, `idempotent_replay_count`.
  - Workers: queue depth, processing latency, DLQ count.
- **Traces**: OpenTelemetry spans on every router + facade + adapter method. Context propagates through queue jobs via ARQ job metadata.
- **Client RUM**: Sentry (browser) for errors + basic performance (TTI, LCP, INP). Opt-in only in tenant settings.

### 12.2 SLIs / SLOs

| SLI | Target |
|---|---|
| Inbox TTI (p75) | < 1.5 s on broadband |
| List scroll FPS | ≥ 55 (1000-row list) |
| Search p95 | < 400 ms (indexed) |
| Send success rate | ≥ 99.5 % / 7-day rolling |
| Sync drain time after reconnect (p95, 100 pending ops) | < 3 s |
| API availability | 99.9 % / 30-day rolling |

### 12.3 Feature flags

- Collection `feature_flags` with `{ key, enabled, rollout: { strategy, percentage?, tenant_allowlist?, user_allowlist? } }`.
- Hook `useFlag(key)` reads from a QueryClient-cached endpoint `GET /v1/flags`; defaults to `false` on miss.
- Used to gate: offline Tier X rollouts, Copilot surfaces, experimental UI.

### 12.4 Rate limits + abuse

- `slowapi` (Redis-backed) middleware. Defaults per user+route:
  - Mutations: 60 / min.
  - Sends: 30 / min, 500 / day.
  - Search: 30 / min.
- Tenant admins can relax per plan; limits log + return `429` with a `retry_after` hint.
- Abuse signals (many failed sends, mass-move) logged to audit log and surfaced to admin.

---

## 13. Python backend hardening

### 13.1 External worker queue (Phase 5)

- Replace `WorkerManager` with **ARQ** over Redis.
- Jobs: `scheduled_send_tick`, `snooze_wake_tick`, `apply_rules(message_id)`, `inbound_poll(account_id)`, `retention_evict`, `rebuild_search_index`.
- At-least-once semantics; handlers are idempotent; DLQ for N retries.
- Graceful shutdown via lifespan.

### 13.2 OIDC / SSO (Phase 4)

- Enable the KeyCloak path already configured in `config/default.yaml`.
- JWKS cache with periodic refresh.
- Claims → `user_id`, `tenant_id`. On first login, provision `User` row.
- Account-level delegation via `AccountUser` table.

### 13.3 Audit log (Phase 4)

- Middleware captures every mutating request outcome; writes to `audit_log` asynchronously via ARQ (fire-and-forget with bounded buffer).
- Query API: `GET /v1/audit?subject_type=&subject_id=` (admin only).
- Retention: default 90 days; TTL index; per-tenant override.

### 13.4 GDPR export / delete (Phase 5)

- `POST /v1/gdpr/export` enqueues a worker that walks all user-owned data, writes a zipped JSON + attachment bundle to storage, and emails a signed link.
- `DELETE /v1/gdpr/user/{id}` enqueues a cascading soft-delete (tombstone) with a 30-day purge worker.

---

## 14. Phased implementation plan

All phases assume **feature-flag gating** for any user-visible change that cannot be rolled back cleanly.

### 14.0 Phase 0 — Docs and housekeeping

**Goal**: single-source roadmap; AGENTS.md reflects reality.

Actions:
1. Write this document (`thoughts/shared/plans/05-roadmap.md`).
2. Delete `01-brd.md`, `02-implementation-plan.md`, `03-design-system.md`, `04-backend-architecture.md`, `mail_backend_facade_spec.md`.
3. Rewrite `thoughts/shared/plans/00-README.md` to point to this document only.
4. Update `AGENTS.md`:
   - Reflect that Calendar (day/week/month), Contacts routes, Signatures UI are shipped.
   - Replace references to Lovable Cloud / Supabase with FastAPI + MongoDB + KeyCloak.
   - Mention `runtime/mail_api/` in the codebase map.
   - Point to `05-roadmap.md` as the only plan document.
5. Add a `runtime/mail_api/README.md` if missing, pointing at §13 / §18 here.

**Estimated effort**: 0.5 day. Zero code changes.

**Exit criteria**: documentation consistent, reviewed, and merged. This phase is itself the artifact being reviewed now.

---

### 14.1 Phase 1 — Client foundation + tenancy

**Goal**: introduce the scaffolding for everything that follows without breaking v1.0.

#### 14.1.1 Client — storage layer

- Add `dexie` to `webmail_ui` dependencies.
- Create `src/lib/db/schema.ts` and `src/lib/db/index.ts` (singleton DB, typed tables per §8.2).
- Migrate `useMailStore` persistence target from `localStorage` to a Dexie-backed storage shim (still behind the current Zustand surface). This keeps v1.0 features working while moving bytes off `localStorage`.

#### 14.1.2 Client — typed API SDK

- Add devDeps: `openapi-typescript`.
- Script `npm run gen:api` in `webmail_ui` that reads `../runtime/mail_api/openapi.json` (committed snapshot) and writes `src/lib/api/types.gen.ts`.
- Hand-written `src/lib/api/client.ts` with `fetch` wrapper (auth header, correlation ID, idempotency key injection, error envelope decoding).

#### 14.1.3 Client — QueryClient mounted

- Create `src/lib/query/client.ts`: a factory returning a fresh `QueryClient` per request (for SSR safety) with the IDB persister attached.
- Mount `<QueryClientProvider>` in `src/routes/__root.tsx`.
- Add `src/lib/query/keys.ts` — central key factories per entity.
- **No data reads switched yet** — we're verifying the pipeline.

#### 14.1.4 Client — central shortcut registry

- Create `src/lib/shortcuts/registry.ts`, `provider.tsx`, and `use-shortcut.ts`.
- Migrate existing in-component shortcuts (`⌘K`, `?`, `j/k`, `e`, `#`, `r`, `a`, `f`, compose shortcuts) to the registry.
- `?` modal reads from the registry.

#### 14.1.5 Backend — tenancy + multi-account models

- Add `tenant_id`, `account_id` fields (nullable during migration) to every Beanie model under `app/adapters/db/`.
- Introduce `Tenant`, `Account`, `AccountUser` models per §6.
- Middleware resolves `tenant_id` from JWT claim (dev mode supplies via config); `account_id` from `X-Account-Id` header or primary-account lookup.
- Seed script creates a default tenant + primary account for the dev user; `seed_mongo` feature gated behind settings.
- Every router dependency passes `tenant_id + account_id + user_id` into facades; facades filter every query on that triple.

#### 14.1.6 Backend — versioning + idempotency infra

- Add `version: int` and `deleted_at: datetime?` to all mutable Beanie models; default `version = 0`.
- `IdempotencyKey` collection with TTL index.
- `services.util.idempotent(request, handler)` helper encapsulating read-through / write-through logic.
- `middleware/idempotency.py` enforces `Idempotency-Key` presence on non-idempotent verbs (configurable allowlist during migration).

#### 14.1.7 Backend — `/v1` prefix + OpenAPI snapshot

- All routers moved under `/v1`.
- Keep legacy unversioned paths as 301s for one release (dev note: client never called them, so we can drop immediately after merge).
- CI step: `uvicorn app.main:app --port 8000` boot → `curl /openapi.json` → fail if differs from `runtime/mail_api/openapi.snapshot.json` without a regeneration commit.

**Deliverables**: no user-visible change. Infrastructure only.

**Estimated effort**: 3–4 engineering days (parallelizable 2 engineers × 2 days).

**Exit criteria**: see §15.1.

---

### 14.2 Phase 2 — API cutover + outbox + optimistic updates

**Goal**: the client reads and writes through TanStack Query + the API for one vertical slice (Inbox list + reading + single-message mutations + send), end-to-end, including an outbox.

#### 14.2.1 Client — vertical slice wiring

- Hooks:
  - `useMessages({ accountId, folderId, view, cursor })` — list query.
  - `useThread({ threadId })` — detail query.
  - `useMessage({ id })` — detail query.
  - Mutations: `useToggleRead`, `useToggleFlag`, `useTogglePin`, `useMoveTo`, `useArchive`, `useRemove`, `useSnooze`, `useCategorize`, `useSendDraft`, `useSaveDraft`.
- Every mutation uses a factory that handles optimistic update, rollback on error, `Idempotency-Key`, `If-Match`, op-log append, invalidation.
- Feature flag `use_api_inbox` toggles the flow per-folder; default off → legacy Zustand read path still works.

#### 14.2.2 Client — outbox (Tier 2 prerequisite)

- Dexie `outbox` and `attachments_blobs` tables.
- Compose saves draft fields into `outbox` on every edit (debounced).
- `useSendDraft` marks `outbox.status = 'queued'`; drain worker posts with attachments chunked.
- Outbox sidebar item + retry/edit/delete affordance.
- UI indicator for connection state in the app header.

#### 14.2.3 Client — op-log scaffold (Tier 3 prerequisite)

- Every mutation appends to `op_log` regardless of online state.
- On success the entry is deleted; on failure marked `failed` with last error.
- Drain worker runs on `online` / `focus` / `visibilitychange` events, plus 60 s timer.

#### 14.2.4 Backend — full CRUD routers with idempotency + version

- Audit every endpoint in `app/api/routers/` for `Idempotency-Key` + `If-Match`.
- `MessageActionRequest` accepts bulk actions with a single idempotency key.
- `POST /v1/drafts/{id}/send` enqueues a scheduled-send job (even for immediate sends, with `run_after = now`) — unifies the code path with scheduled send and undo-send (Phase 4).

#### 14.2.5 Backend — attachments chunked upload

- `POST /v1/attachments/init` → `{ upload_id, chunk_size, max_size }`.
- `PATCH /v1/attachments/{upload_id}/chunk` with `Content-Range`.
- `POST /v1/attachments/{upload_id}/finalize` → validates checksum, persists attachment row, returns `Attachment`.
- `AntiVirusAdapter.scan()` called in `finalize` (default no-op).

**Deliverables**: Inbox reads + core mutations + compose send run through the API when the flag is enabled. Offline send works via outbox. Remaining surfaces (search, rules, templates, etc.) still use Zustand — scheduled for Phase 3 alongside the rest of the sync plumbing.

**Estimated effort**: 5–7 engineering days.

**Exit criteria**: see §15.2.

---

### 14.3 Phase 3 — Offline tiers 1–4

**Goal**: airplane-mode operation end-to-end, including reconciliation.

#### 14.3.1 Service worker (Tier 1)

- `vite-plugin-pwa` in `injectManifest` mode.
- Precache shell + static assets (hashed by Vite).
- Runtime cache strategies:
  - API lists (`GET /v1/messages`, `/v1/threads`, `/v1/folders`): `NetworkFirst` with 5 s timeout, fallback to IDB reader via Clients API messaging.
  - API detail: `StaleWhileRevalidate`.
  - `GET /v1/sync`: never cached by SW.
- Update flow: silent SW install; on `update available` show a "New version ready" toast with "Reload".

#### 14.3.2 Dexie cache policy

- Per §9.1 — inbox/focused hot cache, on-demand bodies, per-thread "Available offline".
- Eviction worker (`src/lib/sync/eviction.ts`) runs on app idle.

#### 14.3.3 Delta sync (Tier 4)

- Backend:
  - `op_log` collection per §6.2.
  - Every mutating facade appends an `OpLogEntry` transactionally.
  - `GET /v1/sync?since=&account_id=&limit=` endpoint; cursor is an opaque base64 of `(tenant_id, account_id, seq)`.
  - Ops include full entity projections for simplicity (dedup upstream compaction can come later).
- Client:
  - `src/lib/sync/delta.ts` — the replay engine: fetches → upserts/deletes in Dexie → invalidates Query keys.
  - Runs on startup, on `online`, and on SSE push (Phase 5 — for v1.1 we poll every 30 s while focused).
  - Per-account `sync_cursor` persisted in Dexie.

#### 14.3.4 Op-log drain + conflict resolution (Tier 3 completion)

- Drain order: delta replay first → then op-log oldest→newest.
- Conflict cards (§9.4) when a `409` returns; user can "Keep server" / "Apply mine".
- Auto-resolves: last-write-wins for read/flag/pin/categorize.
- Explicit user choice for move/archive/delete conflicts.

#### 14.3.5 Expand vertical slice to all surfaces

- Switch all remaining Zustand mail reads/writes (search, rules, templates, signatures, saved searches, categories, preferences) to query/mutation hooks.
- Delete `mail-store.ts`; shrink `compose-store.ts` to a thin `{ openDraftId }` reference into Dexie.
- Feature-flag removal cleanup — `use_api_inbox` and related flags removed once the surface is stable.

**Deliverables**: full offline support; Zustand reduced to UI-only state.

**Estimated effort**: 6–8 engineering days.

**Exit criteria**: see §15.3.

---

### 14.4 Phase 4 — BRD hardening

**Goal**: make the product safe and professional for real mail.

Sub-deliverables (each shippable independently, order flexible):

#### 14.4.1 Safe rendering (§10.1–10.3)

- `isomorphic-dompurify` dep.
- `MailBodyRenderer` with sandboxed iframe + CSP `srcdoc`.
- Remote-image blocker + per-sender trust memory (`trusted_senders` Dexie table, synced via preferences).
- `GET /v1/proxy/image?src=` endpoint.
- CSP response headers in production (env-aware).

#### 14.4.2 Sender trust UI (§10.4)

- `FirstTimeSenderBanner`, `ExternalSenderBanner`, `AuthResultsBadge`, `SenderTrustBanner`.
- Backend populates `first_time_sender`, `external`, `authentication_results` on message ingestion.

#### 14.4.3 Undo-send + scheduled-send cancel (§10.6)

- Client: `Undo-send window` preference; send mutation delays final dispatch via the scheduler path.
- Backend: `POST /v1/drafts/{id}/cancel-send` implementation; `delivery_state` transitions.

#### 14.4.4 Threading spec (§10.7)

- Client: unchanged — just consumes server `thread_id`.
- Backend: message-ingestion path updated to use RFC 2822 headers + provider thread ID; orphan reconciliation worker.

#### 14.4.5 Attachments

- Inline image `cid:` rewrite to `/v1/attachments/{id}/inline?token=` on render.
- Chunked upload (already landed Phase 2) — UI polish: per-file progress + pause/resume.
- Size cap enforcement (server + client).

#### 14.4.6 Adapters scaffolded (default disabled)

- `AntiVirusAdapter` protocol + `NoOpScanner` + `ClamAVScanner` stub (TODO enablement §17).
- `PreviewAdapter` protocol + `PDFJsPreview` (client-side) + Office stub (TODO enablement §17).
- `PushAdapter` protocol + `VAPIDPushSender` stub; client SW registers for push behind a feature flag.

#### 14.4.7 SSO (KeyCloak) (§13.2)

- Flip `auth.enabled = true`; issuer & JWKS wired.
- Login flow: `/login` redirects to KeyCloak; `/callback` stores tokens; silent refresh.
- Dev mode (no KeyCloak) retained for local testing.

#### 14.4.8 Audit log (§13.3)

- Middleware → `audit_log` writer.
- `GET /v1/audit?...` admin endpoint.

#### 14.4.9 i18n extraction

- Choose between `react-intl` and `@lingui/core` (recommendation: `@lingui/core` for automatic extraction + ICU support).
- Extract every user-visible string.
- Ship `en-US` only; structure ready for additional locales.
- Mark RTL audit as TODO (§17 candidate — we may roll this in or defer; flag for review).

#### 14.4.10 Import / export / print

- `GET /v1/messages/{id}/eml` → download.
- `POST /v1/import/mbox` → enqueues a worker.
- Client "Print" and "Save as PDF" via CSS print stylesheet + browser-native dialog.

#### 14.4.11 Saved searches

- CRUD endpoints + client UI.
- Saved searches appear in the sidebar under a "Saved" group; clicking restores the facet state.

**Estimated effort**: 10–14 engineering days (parallelizable).

**Exit criteria**: see §15.4.

---

### 14.5 Phase 5 — Operations hardening

**Goal**: run in production with confidence.

- Replace `WorkerManager` with ARQ + Redis (`runtime/mail_api/app/workers/arq_app.py`).
- OpenTelemetry instrumentation: `opentelemetry-instrumentation-fastapi`, `pymongo`, `httpx`; OTLP exporter.
- `/metrics` via `prometheus-fastapi-instrumentator`.
- Sentry (client + server).
- Rate limits via `slowapi` (Redis-backed).
- Feature flags: collection + `GET /v1/flags` + `useFlag` hook.
- GDPR export / delete endpoints + workers.
- `AuthMiddleware` hardening: token revocation checks, audience validation.
- Chaos testing: induced outbox backlog, induced sync lag, induced provider failure.

**Estimated effort**: 6–8 engineering days.

**Exit criteria**: see §15.5.

---

### 14.6 Phase 6 — Microsoft Graph provider

**Goal**: real enterprise mail.

- `MicrosoftGraphTransportAdapter` (send, list folders, list messages, delta).
- `MicrosoftGraphInboundAdapter` (webhook `/v1/providers/ms/webhook`; subscription renewal worker).
- OAuth 2 auth-code + PKCE flow for tenant admins; multi-tenant registration.
- Account provisioning UX: "Add Microsoft account" in account settings.
- Mapping: Graph `conversationId` → our `thread_id`; Graph folder tree → our folder tree; Graph delta tokens persisted in `Account.sync_cursor`.
- Fallback polling if webhook subscriptions fail.

**Estimated effort**: 10–14 engineering days.

**Exit criteria**: see §15.6.

---

## 15. Acceptance criteria per phase

### 15.1 Phase 1 exit

- `npm run build` and `npm run dev` both succeed in `webmail_ui/`.
- `npm run gen:api` regenerates `types.gen.ts` without diff when OpenAPI is unchanged.
- All v1.0 features work exactly as before (regression baseline).
- `mail-store`'s persistence target is Dexie; `localStorage.getItem('psense-mail-data') === null`.
- Every shortcut listed in the `?` modal is driven by the registry.
- Backend: `GET /v1/health` returns OK; all routers mounted under `/v1`; OpenAPI snapshot committed.
- Every Beanie document read from the DB carries `tenant_id`, `account_id`, `version` fields (seeded to dev defaults for backfill).
- A documented `Idempotency-Key` check returns a replayed response for a mutating call made twice.

### 15.2 Phase 2 exit

- With `use_api_inbox` on, the Inbox reads from the API, not Zustand.
- Go offline (DevTools); archive a message → UI updates; go online → API receives the archive.
- Compose + send offline → message appears in the "Outbox" sidebar item; reconnect → it sends; `op_log` drains.
- Killing a tab mid-send does not drop the outbox entry; reopen completes the send.
- `curl -X POST ... -H 'Idempotency-Key: X'` twice with the same body returns the identical response both times with `X-Idempotency-Replay: true` on the second.

### 15.3 Phase 3 exit

- First-load while offline: the app shell renders and shows cached inbox contents.
- After 100 offline mutations, reconnect drains in < 3 s at p95 against a local backend.
- Simultaneously archiving the same message from two tabs triggers a deterministic merge (no duplicates; conflict card optional by policy).
- Airplane mode test suite passes (scripted).

### 15.4 Phase 4 exit

- No raw `dangerouslySetInnerHTML` outside the iframe renderer.
- Remote images blocked by default; "Show images" persists per sender.
- First-time and external sender banners render on representative test messages.
- Undo-send within the configured window aborts the send; outside the window returns a graceful "too late" message.
- An incoming reply threads correctly using `In-Reply-To` even when subject differs.
- KeyCloak login works end-to-end against a dev realm.
- Audit log records each mutation with correlation ID.
- All user-visible strings load through the i18n formatter.
- Saved searches round-trip across reloads.

### 15.5 Phase 5 exit

- Graceful deploy restart does not drop scheduled-send jobs (re-read from Redis).
- Prometheus scrape returns non-empty metrics; Grafana dashboard imports cleanly.
- Rate-limit test: > 60 mutations in 10 s returns `429` with `Retry-After`.
- GDPR export for a test user produces a zipped bundle containing messages, preferences, and signatures.
- Feature flag toggles propagate in < 60 s.

### 15.6 Phase 6 exit

- A real Microsoft 365 account's inbox loads, threads, and archives correctly.
- A Graph webhook triggers a new-message notification that arrives in the UI within 5 s (airplane-mode-less).
- Sending from PSense Mail posts correctly in the user's Sent folder in Outlook.

---

## 16. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| IDB quota exceeded on power-users with large mailboxes | M | H | Quota monitor + aggressive eviction (§9.5); cap "Available offline" bodies in MB. |
| Dexie schema migrations break client data | L | H | Versioned Dexie migrations; every migration dry-run in CI on a snapshot. |
| Op-log + delta-sync introduces duplicate writes | M | H | Server enforces idempotency by key; op-log entries carry unique client seq; reconciliation tests. |
| Mailbox-scale search on Mongo degrades p95 | M | M | Protocol keeps Meilisearch escape hatch; plan to benchmark at 500 k messages before Phase 6. |
| Undo-send window causes mis-sends if scheduler lags | L | H | Undo-send is client-hold only; server send runs atomically when `run_after` expires; cancel is a DB-level compare-and-swap on `delivery_state`. |
| KeyCloak availability blocks login | M | H | JWKS cached in-process with 24 h fallback; health probe excludes auth; degraded mode shows read-only cache for last session. |
| HTML sanitizer bypass | L | H | Sandboxed iframe with no `allow-scripts`; CSP in `srcdoc`; regular DOMPurify updates; pen-test as part of Phase 4 acceptance. |
| Service worker cache staleness after deploy | M | M | Cache bust on app-version change; "New version ready" toast; SW skips-waiting only on explicit user click. |
| Multi-account pollution (wrong account shown) | L | H | `account_id` in every query key; strict server-side filter; end-to-end test with two accounts. |
| Migration drops user data | L | H | Phase 1 migration is additive (new fields, nullable). No data write before backup. Backup + restore runbook documented. |
| OpenAPI drift between client and server | M | M | CI check fails on drift; generator run on every PR. |

---

## 17. TODO backlog

### 17.1 Deferred to a later major (R — not in v1.x scope)

| Item | Why deferred | Prerequisite |
|---|---|---|
| **S/MIME (sign/encrypt/verify)** | Specialized: X.509 key management, web crypto, cert-store UX, GAL integration. 4–8 week dedicated project. | Customer demand; enterprise tier. |
| **PGP / OpenPGP** | Specialized: key discovery (WKD, keyservers), passphrase UX, web crypto. Similar budget to S/MIME. | Customer demand. |
| **eDiscovery / Legal hold / Retention-lock** | Compliance engineering: immutable storage, chain of custody, cross-tenant search, legal-hold UI. | Regulated-industry customer. |
| **`.pst` (Outlook PST) import** | Proprietary format; OSS parsers (`libpff`, `pypff`) are flaky C bindings. Most vendors use a separate paid ingest tool. | Customer demand; consider as offline CLI. |
| **Data residency (EU/US per tenant)** | Infra/ops project: multi-region deploy, data-at-rest region pinning. Not application code. | Infra rollout plan. |

### 17.2 Pluggable but not enabled in v1.x (O — adapter shell ships, integration later)

| Item | Adapter | Default |
|---|---|---|
| **Antivirus scanning** | `AntiVirusAdapter` | `NoOpScanner`. ClamAV sidecar or SaaS enablement later. |
| **Office format preview** | `PreviewAdapter` (Office variant) | PDF preview enabled (client `pdfjs-dist`); Office (doc/xlsx/pptx) requires Gotenberg / LibreOffice-headless sidecar. |
| **Web push notifications (VAPID)** | `PushAdapter` | `NoOpPush`. Enablement requires VAPID keys + push-dispatch worker. |
| **Meilisearch / OpenSearch for search** | `SearchAdapter` | `MongoSearchAdapter`. Swap when message volume exceeds Mongo FTS comfort zone (~500 k msgs). |

### 17.3 Noted but scope-TBD

- **RTL layout audit** — one week of component-level testing + logical-property conversions. Candidate for late Phase 4 or early Phase 5.
- **Mobile-native apps** — post-v1 metrics decision.
- **AI Copilot** — requires separate plan; hooks into the same data spine.
- **Delegation UI** — schema supports it (`AccountUser` roles); no UX in v1.x.

---

## 18. Python façade spec

*(Preserved from `mail_backend_facade_spec.md` for reference — still the authoritative shape for `runtime/mail_api/app/services/`.)*

### 18.1 Design principles

- Async-first.
- Provider-agnostic.
- Typed and testable.
- Idempotent on risky writes.
- Resilient under partial outages.
- Separation of HTTP layer and domain layer.

### 18.2 Package layout

```
app/
  api/routers/          # mailbox, messages, drafts, search, attachments, admin, ...
  domain/               # enums, errors, models, requests, responses, protocols
  services/             # mail_facade, compose_facade, search_facade, attachment_facade, admin_facade
  adapters/             # storage, search, transport, inbound, db, events, policy
  workers/              # send, index, retention, scheduler, snooze, inbound poller, retry
  middleware/           # auth, correlation, error-handler, idempotency, rate-limit, audit
  seed/                 # demo data
  main.py
```

### 18.3 Core domain states

- **DeliveryState**: `draft | queued | sending | sent | failed_retryable | failed_permanent | scheduled | cancelled`.
- **Folder kinds**: `inbox | focused | other | drafts | sent | archive | snoozed | flagged | deleted | junk | custom`.
- **Message actions**: archive, delete, restore, move, mark_read, mark_unread, flag, unflag, pin, unpin, snooze, unsnooze, categorize, uncategorize.

### 18.4 Reliability requirements

- Every mutating façade method accepts an optional `idempotency_key`.
- Updates support optimistic concurrency via `expected_version`.
- Domain services raise structured domain exceptions, never raw adapter exceptions.
- Search / index / transport outages degrade into typed `ProviderUnavailableError` or `RetryableDeliveryError`.
- Failed sends preserve the original draft/message intent for replay and inspection.

### 18.5 Façades

- **MailFacade**: list folders, list threads, fetch message/thread, move/archive/delete/restore, mark read/unread, flag/pin/snooze/categorize, bulk actions.
- **ComposeFacade**: create draft, patch draft, validate recipients/body/attachments, send draft, retry failed send, schedule send, cancel-send.
- **SearchFacade**: structured search, suggestions, facets, recent searches.
- **AttachmentFacade**: initialize upload, chunk upload, finalize upload, read metadata, authorize download, scan (via adapter).
- **AdminFacade**: health report, seed demo data, replay failed sends, reindex, purge test data, diagnostics.

### 18.6 Domain exception hierarchy

```
MailDomainError
├── NotFoundError
├── ValidationError
├── ConflictError
├── ConcurrencyError
├── PolicyDeniedError
├── ProviderUnavailableError
├── RateLimitedError
├── RetryableDeliveryError
└── PermanentDeliveryError
```

### 18.7 Operational guidance

- Keep provider-specific fields under `adapter_meta`.
- Use a local transport adapter in development that can feed MailPit or an in-memory sink.
- Add contract tests for façade behavior before wiring full adapters.
- Prefer cursor pagination for thread/message list APIs.
- Expose correlation IDs in route responses and logs for troubleshooting.

---

## 19. Glossary

| Term | Meaning |
|---|---|
| **Account** | A mail identity (e.g. `avery@psense.ai`). Multiple accounts per user are supported. |
| **Adapter** | A concrete implementation of a protocol — transport, storage, search, AV, preview, push. |
| **Delta sync** | `GET /v1/sync?since=<cursor>` — server op-log stream used by the client to reconcile offline changes. |
| **Dexie** | Typed IndexedDB wrapper used for the client's durable cache, outbox, op-log, blobs. |
| **Idempotency key** | Header `Idempotency-Key` used to safely retry mutating requests. |
| **Op-log (client)** | Queue of pending mutations persisted in IDB; drained on reconnect. |
| **Op-log (server)** | Append-only collection emitting change events consumed by the delta-sync endpoint. |
| **Outbox** | Client-side queue of compose drafts waiting to be sent. |
| **Tenant** | An organization or workspace; the top-level isolation boundary. |
| **Tombstone** | A soft-deleted record kept for sync reconciliation until a retention-based purge. |
| **Version (entity)** | Monotonic integer incremented on each update; used for optimistic concurrency (`If-Match`). |

---

*End of roadmap.*
