# PSense Mail — Gap & Enhancement Analysis

> Generated: April 2026  
> Based on: `README.md`, `AGENTS.md`, and full codebase review  
> Status: Pre-implementation reference

---

## What's Genuinely Solid

The foundation is well-engineered. The domain model is thorough (tenancy, versioning, soft deletes, op-log, idempotency records all in place). The adapter protocol pattern is clean. The POP3 adapter + MIME parser + seen-store is the most complete vertical slice. The error hierarchy is well-structured. The middleware stack (auth, correlation, idempotency) is production-quality.

---

## Critical Gaps (Blockers for Real Use)

### 1. Frontend is entirely mocked — no live API wiring
The UI runs on `mail-store.ts` (Zustand with static seed data). TanStack Query is mounted but hooks in `hooks/queries/` and `hooks/mutations/` are scaffolded, not wired. No user can actually send or receive mail through the UI today. This is the single biggest gap.

### 2. HTML rendering is unsafe
`body_html` is stored and presumably rendered without DOMPurify or a sandboxed iframe. This is a XSS vector in a mail client — a critical security gap, not a Phase 4 nice-to-have.

### 3. Auth is disabled by default with no path to enable it safely
`auth.enabled=false` is fine for dev, but the JWT validation path in `auth.py` fetches JWKS on every request (no caching). In production this would hammer KeyCloak and fail under load. JWKS caching needs to land before auth can be turned on.

### 4. Inbound poller is single-tenant/single-account
`InboundPollerWorker` takes a single `cache_user_id`. Multi-account support (multiple POP3 accounts per user, multiple tenants) requires a poller-per-account model or a dispatcher that manages N pollers.

### 5. `list_folders` is N+1 query heavy
For each folder it fires 2 separate `count()` queries. With 15 system folders that's 30 DB round-trips per sidebar render. Needs aggregation pipeline.

---

## Security Gaps

### 6. No rate limiting
No per-user or per-tenant rate limiting on any endpoint. The search endpoint in particular is unbounded.

### 7. `provider_meta` stores credentials in plaintext
`AccountDoc.provider_meta` holds OAuth tokens and POP3 passwords. These need field-level encryption (e.g., Fernet) before any multi-user deployment.

### 8. Attachment upload has no AV scanning integration
`AvState` enum exists on `MailAttachmentMeta` but the attachment facade doesn't call any scanner. Files are stored with `AvState.UNKNOWN` indefinitely.

### 9. CORS is too permissive in dev
`cors_origins` defaults to `["http://localhost:3000"]` which is fine, but there's no enforcement that production overrides this. A misconfigured prod deploy would be wide open.

---

## Data Model Gaps

### 10. `MessageDoc` mixes `user_id` and `account_id` inconsistently
The comment says "prefer `account_id` going forward" but `user_id` is still the primary query field in most indexes and all facade queries. This dual-field state will cause bugs when a user has multiple accounts — messages from account A will appear in account B's queries.

### 11. Thread deduplication is fragile
The subject+participant fallback in `_resolve_thread` scans the last 50 threads linearly. For active mailboxes this will produce false positives (e.g., two separate "Hello" threads merged). The `message_id_header` lookup also queries `adapter_meta` which has no index.

### 12. `OpLogEntry.seq` uses `time.time() * 1000`
Millisecond timestamps are not monotonic under clock skew or concurrent writes. Two entries written in the same millisecond get the same `seq`, breaking delta sync ordering. Needs an atomic counter (MongoDB `$inc` on a sequence document, or a ULID-based seq).

### 13. No pagination on threads list
`GET /threads` has no cursor pagination in the router. Large mailboxes will OOM the response.

---

## Missing Features (Product Completeness)

### 14. No push notifications / real-time updates
The frontend polls or waits for user action. There's no WebSocket or SSE endpoint for new-mail notifications. The op-log exists but nothing pushes it to the client.

### 15. No contact/address book integration
Contacts routes exist in the frontend but are placeholder. There's no `ContactDoc` model, no contact search, no auto-complete in the compose `To:` field backed by real data.

### 16. Calendar is entirely placeholder
Routes exist, components exist, but there's no `EventDoc`, no iCal import/export, no CalDAV adapter. It's UI chrome with no backend.

### 17. No IMAP adapter
POP3 is implemented. Gmail uses the REST API. But IMAP (the dominant enterprise protocol) has no adapter. This limits the "any provider" claim significantly.

### 18. No Microsoft Graph adapter
Listed as Phase 6 but it's a hard requirement for enterprise customers on Microsoft 365. Without it, the "enterprise" positioning is incomplete.

### 19. Attachment preview generation is unimplemented
`PreviewState` enum exists on `MailAttachmentMeta` but no preview worker generates thumbnails or PDF previews.

### 20. No GDPR/data export endpoint
Listed as planned but absent. Required for EU deployments.

---

## Observability & Operations Gaps

### 21. No structured health check beyond `/health`
The adapter `health_check()` protocol exists but nothing aggregates adapter health into the `/health` endpoint. A failing POP3 connection is invisible to monitoring.

### 22. No OpenTelemetry instrumentation
`structlog` is used for logging but there are no traces, no spans, no metrics. Debugging production issues requires log archaeology.

### 23. Workers have no dead-letter queue
The retry worker exists but failed messages after `max_attempts` are just logged. There's no DLQ, no alerting, no admin UI to inspect stuck messages.

### 24. No database migration tooling
Beanie handles schema on startup but there's no migration framework (e.g., Mongrations). Schema changes to existing collections require manual intervention.

---

## Developer Experience Gaps

### 25. `gen:api` requires a running backend
The OpenAPI type generation step (`npm run gen:api`) requires the backend to be up. This breaks CI pipelines that don't spin up the full stack. The OpenAPI spec should be committed to the repo.

### 26. No E2E test suite
Unit tests cover the backend well (POP3, facades, idempotency). But there are no E2E tests (Playwright/Cypress) covering the full browser→API flow.

### 27. No CI/CD pipeline definition
No `.github/workflows/` or equivalent. The deployment checklist is manual.

---

## Enhancement Opportunities (Beyond Gaps)

### 28. AI Copilot surface
The product positions against Superhuman. Superhuman's key differentiator is AI triage. A `CopilotFacade` with summarization, smart reply, and priority scoring (using an LLM via a pluggable adapter) would be a strong differentiator and fits the existing adapter pattern perfectly.

### 29. Focused Inbox ML scoring
`is_focused` is a boolean set manually. A lightweight classifier (sender history + engagement signals) could auto-score messages, making Focused Inbox genuinely useful rather than a manual toggle.

### 30. Offline-first compose
The outbox in Dexie is designed but not wired. Completing this (draft → IDB outbox → service worker background sync → API) would make PSense Mail usable on flaky connections — a real enterprise differentiator.

### 31. Webhook/event bus for integrations
No outbound webhook system. Enterprise customers want to pipe mail events (new message, rule triggered) into Slack, Zapier, or internal systems. An `EventBusAdapter` protocol + webhook delivery worker would unlock this.

---

## Prioritized Recommendations

| Priority | # | Item | Why |
|---|---|---|---|
| P0 | 2 | Fix HTML rendering (XSS) | Security — ship nothing else until this is done |
| P0 | 1 | Wire TanStack Query to live API | Product is non-functional without this |
| P1 | 3 | JWKS caching in auth middleware | Required before auth can be enabled |
| P1 | 10 | Fix `user_id`/`account_id` dual-field inconsistency | Data correctness for multi-account |
| P1 | 12 | Fix `OpLogEntry.seq` monotonicity | Delta sync correctness |
| P1 | 7 | Encrypt `provider_meta` credentials | Security for any multi-user deploy |
| P2 | 4 | Multi-account poller dispatcher | Core multi-account feature |
| P2 | 5 | Fix N+1 in `list_folders` | Performance at scale |
| P2 | 11 | Add index on `adapter_meta.message_id_header` | Thread resolution correctness |
| P2 | 14 | SSE/WebSocket for real-time new mail | UX parity with modern clients |
| P3 | 17 | IMAP adapter | Provider coverage |
| P3 | 15 | Contact model + compose autocomplete | Product completeness |
| P3 | 22 | OpenTelemetry instrumentation | Operational readiness |
| P3 | 25 | Commit OpenAPI spec to repo | CI/CD unblocked |

---

## Next Steps

Pick a priority area and create a spec:

- **P0 security** → HTML sanitization spec (`DOMPurify + sandboxed iframe`)
- **P0 product** → TanStack Query API wiring spec (Phase 2 cutover)
- **P1 data** → `account_id` migration + multi-account poller spec
- **P1 infra** → JWKS caching + auth hardening spec
- **P3 feature** → IMAP adapter spec
- **P3 feature** → Contacts + address book spec
