# Harden Python Mail Backend — Comprehensive Plan

## Critical Evaluation Summary

**Strengths (already solid):**
- Async-first with proper await throughout
- Clean domain error hierarchy (11 exception types, proper HTTP mapping)
- Provider-agnostic adapter protocols (transport, inbound, search, file storage)
- Cursor-based pagination, Beanie ODM, middleware stack
- Flexible config (YAML + env vars + Pydantic)

**Critical Gaps Found (ordered by severity):**

| # | Gap | Severity | Impact |
|---|-----|----------|--------|
| 1 | SearchAdapter protocol exists but is NEVER used — SearchFacade queries MongoDB directly | High | Defeats adapter abstraction; can't swap search backends |
| 2 | Idempotency keys accepted but never deduplicated | High | Duplicate sends, duplicate mutations possible |
| 3 | Optimistic concurrency missing in MailFacade.apply_action | High | Silent data loss under concurrent edits |
| 4 | Hardcoded sender "avery@psense.ai" in ComposeFacade | High | All users send as the same address |
| 5 | Scheduled-send field exists but no scheduler worker | Medium | Feature advertised but non-functional |
| 6 | Failed-send retry is manual only — no automatic retry worker | Medium | Transient failures require user intervention |
| 7 | Inbound threading creates thread_id = message_id (no real threading) | Medium | Conversations never group properly |
| 8 | NAS file storage has no atomic writes | Medium | Truncated files on partial write failures |
| 9 | No retry/circuit-breaker on adapter calls | Medium | Single adapter failure crashes the request |
| 10 | Workers lack graceful shutdown for in-flight tasks | Medium | Data loss on restart |
| 11 | Admin endpoints have no role-based authorization | Low | Any authenticated user can seed/wipe data |
| 12 | No docstrings, no OpenAPI annotations on routes | Low | Poor API discoverability |
| 13 | Test coverage is minimal (3 basic tests) | High | Regressions undetectable |
| 14 | Out-of-office auto-reply / notification prefs not wired | Low | Models exist but never triggered |

---

## Task 1: Wire SearchAdapter Protocol into SearchFacade

**Problem:** `app/services/search_facade.py` builds MongoDB `$regex` queries directly instead of delegating to the `SearchAdapter` protocol defined in `app/adapters/protocols.py`. The `MongoSearchAdapter` and `InMemorySearchAdapter` exist but return empty results.

**Changes:**
- `app/adapters/search/mongo.py` — Move the MongoDB query logic from SearchFacade into `MongoSearchAdapter.search()` and `MongoSearchAdapter.suggest()`
- `app/adapters/search/memory.py` — Implement in-memory search with simple string matching for tests
- `app/services/search_facade.py` — Refactor to delegate all querying to `self._search_adapter` (injected via registry), keeping only facet-building and response mapping in the facade
- `app/adapters/protocols.py` — Ensure `SearchAdapter.search()` signature accepts the structured query DTO and returns raw results the facade can map

---

## Task 2: Implement Idempotency Deduplication

**Problem:** `idempotency_key` is accepted in `ComposeRequest` and `MessageActionRequest` but never checked. Duplicate POST/PUT calls will create duplicate side effects.

**Changes:**
- `app/domain/models.py` — Add `IdempotencyRecord` Beanie document (key, user_id, response_hash, created_at, TTL index)
- `app/services/compose_facade.py` — Before `send_draft`, check `IdempotencyRecord` for existing key; if found, return cached response; if not, execute and store
- `app/services/mail_facade.py` — Same pattern in `apply_action`
- `app/adapters/db/mongo.py` — Register `IdempotencyRecord` in `init_beanie` document list
- TTL: 24 hours (configurable via settings)

---

## Task 3: Add Optimistic Concurrency to MailFacade

**Problem:** `MailFacade.apply_action` mutates messages without checking `expected_version`. ComposeFacade already does this for drafts — MailFacade should follow the same pattern.

**Changes:**
- `app/domain/requests.py` — Ensure `MessageActionRequest` has `expected_version: int | None`
- `app/services/mail_facade.py` — In `apply_action`, add version check: query filter `{"_id": msg_id, "version": expected_version}`, raise `ConcurrencyError` if no match; increment version on success
- `app/domain/models.py` — Add `version: int = 1` field to `MessageDoc` if not present, with `before_save` hook to auto-increment

---

## Task 4: Fix Sender Address Configuration

**Problem:** `ComposeFacade.send_draft` hardcodes `from_address = "avery@psense.ai"`. Should use the authenticated user's email.

**Changes:**
- `app/services/compose_facade.py` — Accept `user_email: str` parameter (from auth context) and use it as `from_address` in `OutboundMessage`
- `app/api/routers/drafts.py` — Pass `request.state.user["email"]` to facade methods
- Fallback: if user email is missing, use a configurable default from settings

---

## Task 5: Build Scheduled-Send and Retry Workers

**Problem:** `DraftDoc.scheduled_for` exists but nothing triggers the send at that time. Failed sends (`delivery_state = failed_retryable`) require manual `retry_send` — no automatic retry.

**Changes:**
- `app/workers/scheduler.py` (new) — `ScheduledSendWorker`: polls for drafts where `scheduled_for <= now()` and `delivery_state == queued`, calls `ComposeFacade.send_draft`
- `app/workers/retry.py` (new) — `RetryWorker`: polls for `DeliveryLogDoc` entries with `delivery_state == failed_retryable` and `retry_count < max_retries`, applies exponential backoff, calls `ComposeFacade.retry_send`
- `app/workers/manager.py` — Register both new workers in `start_all()` / `stop_all()`
- `config/default.yaml` — Add `workers.scheduler_interval_sec: 30` and `workers.retry_max_attempts: 3`, `workers.retry_backoff_base_sec: 60`

---

## Task 6: Implement Proper Inbound Message Threading

**Problem:** `InboundPollerWorker` sets `thread_id = message_id` for every inbound message, so conversations are never grouped.

**Changes:**
- `app/workers/inbound_poller.py` — After converting inbound message, look up existing thread by `In-Reply-To` / `References` headers, OR by normalized subject + overlapping participants; assign existing `thread_id` if found, else create new thread
- `app/services/mail_facade.py` — Ensure `_refresh_thread` is called after inbound message insertion
- `app/domain/models.py` — Add `in_reply_to: str | None` and `references: list[str]` fields to `MessageDoc`

---

## Task 7: Harden Adapter Resilience

**Problem:** No retry logic, no circuit breaker, no atomic file writes, no graceful worker shutdown.

**Changes:**
- `app/adapters/file_storage/nas.py` — Implement atomic writes (write to `.tmp` file, then `os.rename`); add retry wrapper for I/O operations
- `app/adapters/transport/mailpit.py` — Add retry with exponential backoff for SMTP connection failures (3 attempts); catch `aiosmtplib` connection errors and raise `RetryableDeliveryError`
- `app/workers/manager.py` — Implement graceful shutdown: set `_running = False`, then `await asyncio.gather(*tasks, return_exceptions=True)` with a timeout; log any in-flight task failures
- `app/middleware/error_handler.py` — For `RateLimitedError`, include `Retry-After` header in response

---

## Task 8: Expand Test Coverage

**Problem:** Only 3 trivial tests exist. No facade, adapter, or integration tests.

**Changes (priority order):**
- `tests/test_compose_facade.py` (new) — Test create/update/save/send/retry draft lifecycle, idempotency dedup, optimistic concurrency failure
- `tests/test_search_facade.py` (new) — Test structured query parsing, facets, suggestions, empty results
- `tests/test_rules_facade.py` (new) — Test rule CRUD, condition matching, action execution
- `tests/test_mail_facade.py` — Expand: test apply_action with concurrency check, folder CRUD, virtual folder counts, thread refresh
- `tests/test_attachments.py` (new) — Test upload/download/delete with NAS adapter, path traversal rejection, size limits
- `tests/test_workers.py` (new) — Test snooze worker moves messages, inbound poller creates threads, scheduler triggers sends
- `tests/conftest.py` — Add fixtures for seeded user, folders, messages, drafts to reduce test boilerplate

---

## Out of Scope (v1.1+, noted but not addressed now)

- Gmail adapter full implementation (requires OAuth flow + Google API client)
- S3/Azure/GCS file storage adapters (stubs remain)
- Out-of-office auto-reply
- Notification preference triggers
- OpenAPI annotations / docstrings (cosmetic, not functional)
- Admin role-based authorization (low risk in dev mode)
- CI/CD pipeline setup

---

## Implementation Order

1. Task 4 (sender fix) — Quick, high-impact correctness fix
2. Task 1 (search adapter wiring) — Architectural fix, enables test isolation
3. Task 3 (optimistic concurrency) — Data integrity
4. Task 2 (idempotency) — Data integrity
5. Task 6 (inbound threading) — Core feature completeness
6. Task 5 (scheduled-send + retry workers) — Feature completeness
7. Task 7 (adapter resilience) — Robustness hardening
8. Task 8 (tests) — Run after each task above, bulk expansion at end
