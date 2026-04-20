# Requirements Document — PSense Mail Hardening

## Introduction

PSense Mail is a production-grade enterprise webmail workspace (FastAPI backend + React 19 frontend). A gap analysis identified 31 items across 7 categories that must be addressed to make the system production-ready, secure, and feature-complete. This document captures the full set of requirements for implementing all 31 improvements comprehensively, robustly, and resiliently.

The improvements span: critical functional gaps (frontend API wiring, XSS safety, auth hardening, multi-account polling, N+1 query elimination), security hardening (rate limiting, credential encryption, AV scanning, CORS enforcement), data model correctness (account_id consistency, thread deduplication, monotonic op-log sequencing, thread pagination), missing product features (real-time push, contacts, calendar, IMAP, Microsoft Graph, attachment previews, GDPR export), observability and operations (structured health checks, OpenTelemetry, dead-letter queue, database migrations), developer experience (committed OpenAPI spec, E2E tests, CI/CD pipeline), and strategic enhancements (AI Copilot, Focused Inbox ML, offline-first compose, webhook/event bus).

---

## Glossary

- **API_Client**: The typed fetch client in `webmail_ui/src/lib/api/client.ts` that injects auth headers, correlation IDs, and idempotency keys.
- **AttachmentFacade**: The backend service at `runtime/mail_api/app/services/attachment_facade.py` responsible for attachment upload, download, and deletion.
- **AV_Scanner**: An antivirus scanning adapter that inspects uploaded attachment bytes for malware.
- **CalDAV_Adapter**: A backend adapter implementing the CalDAV protocol for calendar synchronisation.
- **CopilotFacade**: A new backend service providing AI-powered email summarisation, smart reply generation, and priority scoring via a pluggable LLM adapter.
- **ContactDoc**: A new Beanie document model representing a contact in the address book.
- **ContactsFacade**: A new backend service providing CRUD operations and search over ContactDoc records.
- **DLQ**: Dead-Letter Queue — a storage collection for worker tasks that have exhausted all retry attempts.
- **DomainError**: The base exception class `MailDomainError` in `runtime/mail_api/app/domain/errors.py`.
- **EventDoc**: A new Beanie document model representing a calendar event.
- **EventBusFacade**: A new backend service that delivers outbound webhook payloads to registered subscriber URLs.
- **GDPR_Exporter**: A new backend service that assembles and streams a complete data export archive for a given user.
- **IMAP_Adapter**: A new inbound adapter implementing the IMAP4rev1 protocol.
- **InboundPollerDispatcher**: A new worker component that manages one `InboundPollerWorker` instance per active mail account.
- **JWKSCache**: An in-process cache for KeyCloak JSON Web Key Sets, keyed by JWKS URI with a configurable TTL.
- **MailFacade**: The backend service at `runtime/mail_api/app/services/mail_facade.py` providing core mail operations.
- **MessageDoc**: The Beanie document model for a mail message in `runtime/mail_api/app/domain/models.py`.
- **MicrosoftGraphAdapter**: A new inbound and transport adapter using the Microsoft Graph REST API.
- **OpLogEntry**: The Beanie document model for the server-side change-feed in `runtime/mail_api/app/domain/models.py`.
- **OTel_SDK**: The OpenTelemetry Python SDK (`opentelemetry-sdk`) used for distributed tracing and metrics.
- **PreviewWorker**: A new background worker that generates thumbnail and PDF previews for stored attachments.
- **QueryClient**: The TanStack Query v5 client instance configured in `webmail_ui/src/lib/query/`.
- **RateLimiter**: A per-user, per-tenant request throttle enforced at the FastAPI middleware layer.
- **ReadingPane**: The frontend component in `webmail_ui/src/components/mail/` that renders message body HTML.
- **SSE_Router**: A new FastAPI router providing a Server-Sent Events stream for real-time new-mail notifications.
- **System**: PSense Mail as a whole, encompassing both the FastAPI backend and the React frontend.
- **TanStack_Query**: The TanStack Query v5 library used for server-state management in the frontend.
- **Tenant**: An organisation or workspace represented by a `TenantDoc` record, the top-level isolation boundary.
- **WorkerManager**: The in-process background task orchestrator at `runtime/mail_api/app/workers/manager.py`.

---

## Requirements

### Requirement 1: Frontend API Wiring — Live Data Cutover

**User Story:** As a user, I want the mail UI to display real messages from the server, so that I can actually send and receive email through PSense Mail.

#### Acceptance Criteria

1. WHEN the application loads, THE QueryClient SHALL fetch messages from `GET /api/v1/messages` via the `useMessages` hook and render them in the message list, replacing all static seed data from `mail-store.ts`.
2. WHEN the application loads, THE QueryClient SHALL fetch folders from `GET /api/v1/folders` via the `useFolders` hook and render them in the sidebar with live unread and total counts.
3. WHEN the application loads, THE QueryClient SHALL fetch thread detail from `GET /api/v1/threads/{thread_id}` via the `useThread` hook and render it in the reading pane.
4. WHEN a user performs a message action (mark read, flag, archive, move, snooze, delete), THE API_Client SHALL call `POST /api/v1/messages/actions` with the appropriate action payload and idempotency key.
5. WHEN a user sends a draft, THE API_Client SHALL call `POST /api/v1/drafts/{id}/send` and THE QueryClient SHALL invalidate the drafts and messages query caches on success.
6. WHEN a user creates, edits, or deletes a draft, THE API_Client SHALL call the corresponding `POST /api/v1/drafts`, `PATCH /api/v1/drafts/{id}`, or `DELETE /api/v1/drafts/{id}` endpoint.
7. WHEN a user creates, renames, or deletes a folder, THE API_Client SHALL call the corresponding mailbox endpoint and THE QueryClient SHALL invalidate the folders cache.
8. WHEN a user saves or updates preferences, THE API_Client SHALL call `PATCH /api/v1/preferences` and THE QueryClient SHALL update the preferences cache optimistically.
9. THE System SHALL remove `mail-store.ts` as a data source for messages, threads, and folders after all query hooks are wired, retaining Zustand only for ephemeral UI state.
10. WHEN a TanStack Query fetch fails with a network error, THE QueryClient SHALL serve the last-persisted Dexie cache and display a non-blocking offline indicator.
11. FOR ALL mutation hooks, THE API_Client SHALL include an `Idempotency-Key` header generated as a UUID v4 per mutation invocation.

### Requirement 2: Safe HTML Rendering — XSS Prevention

**User Story:** As a user, I want to read HTML email bodies safely, so that malicious senders cannot execute scripts in my browser session.

#### Acceptance Criteria

1. WHEN the ReadingPane renders a message with a non-null `body_html` field, THE ReadingPane SHALL pass the HTML through DOMPurify with a strict allowlist before inserting it into the DOM.
2. WHEN the ReadingPane renders a message with a non-null `body_html` field, THE ReadingPane SHALL render the sanitised HTML inside a sandboxed `<iframe>` element with the `sandbox` attribute set to `allow-same-origin` only, preventing script execution, form submission, and top-level navigation.
3. WHEN DOMPurify removes one or more elements or attributes from `body_html`, THE ReadingPane SHALL log the sanitisation event to the browser console at the `warn` level without surfacing an error to the user.
4. WHEN `body_html` is null and `body_text` is non-null, THE ReadingPane SHALL render the plain-text body in a `<pre>` element with CSS `white-space: pre-wrap` without invoking DOMPurify.
5. WHEN both `body_html` and `body_text` are null, THE ReadingPane SHALL display an empty-state message reading "No message body".
6. THE System SHALL install `dompurify` and `@types/dompurify` as production dependencies in `webmail_ui/package.json`.
7. WHEN an external image is referenced in `body_html`, THE ReadingPane SHALL block the image by default and display a "Show images" prompt; WHEN the user clicks "Show images", THE ReadingPane SHALL reload the iframe content with images unblocked for that message only.

### Requirement 3: JWKS Caching in Auth Middleware

**User Story:** As a system operator, I want the authentication middleware to cache JWKS keys, so that KeyCloak is not hammered on every request and auth remains functional under load.

#### Acceptance Criteria

1. WHEN `auth.enabled` is true and the `AuthMiddleware` validates a JWT, THE JWKSCache SHALL serve the cached key set if the cache entry is younger than `auth.jwks_cache_ttl_seconds` (default: 300).
2. WHEN the JWKSCache entry is absent or expired, THE AuthMiddleware SHALL fetch the JWKS from `auth.jwks_uri`, store the result in the JWKSCache with the current timestamp, and use it to validate the token.
3. WHEN the JWKS fetch fails and a stale cache entry exists, THE AuthMiddleware SHALL use the stale entry and log a warning at the `WARN` level including the fetch error message.
4. WHEN the JWKS fetch fails and no cache entry exists, THE AuthMiddleware SHALL return HTTP 503 with error code `AUTH_UNAVAILABLE`.
5. THE JWKSCache SHALL be an in-process singleton scoped to the FastAPI application lifespan, not a per-request object.
6. THE System SHALL add `auth.jwks_cache_ttl_seconds` as a configurable integer field in `AuthConfig` with a default value of 300.
7. WHEN `auth.enabled` is false, THE AuthMiddleware SHALL not instantiate or consult the JWKSCache.

### Requirement 4: Multi-Account Inbound Poller Dispatcher

**User Story:** As a user with multiple mail accounts, I want all my accounts to be polled for new mail, so that messages from every account appear in the UI without manual intervention.

#### Acceptance Criteria

1. WHEN the application starts, THE InboundPollerDispatcher SHALL query `AccountDoc` for all active (non-deleted) accounts whose `provider` field matches a polling-capable provider (`pop3`, `mailpit`, `imap`).
2. FOR EACH active account, THE InboundPollerDispatcher SHALL start one `InboundPollerWorker` instance scoped to that account's `account_id` and `owner_user_id`.
3. WHEN a new account is created via `POST /api/v1/accounts`, THE InboundPollerDispatcher SHALL start a new `InboundPollerWorker` for that account within 5 seconds without restarting the application.
4. WHEN an account is deleted via `DELETE /api/v1/accounts/{id}`, THE InboundPollerDispatcher SHALL stop and remove the corresponding `InboundPollerWorker` within 5 seconds.
5. WHEN an `InboundPollerWorker` encounters a `ProviderUnavailableError`, THE InboundPollerDispatcher SHALL apply exponential backoff starting at 60 seconds, doubling on each consecutive failure, capped at 3600 seconds, before retrying that account's poller.
6. THE InboundPollerDispatcher SHALL replace the single `cache_user_id` constructor parameter on `InboundPollerWorker` with `account_id` and `owner_user_id` parameters, and all messages ingested by a worker SHALL carry the correct `account_id` and `user_id` fields.
7. WHEN the application shuts down, THE InboundPollerDispatcher SHALL stop all managed `InboundPollerWorker` instances within the existing `_SHUTDOWN_TIMEOUT` of 10 seconds.

### Requirement 5: Folder Counts Aggregation — Eliminate N+1 Queries

**User Story:** As a user, I want the sidebar to load quickly even with many folders, so that navigating between folders is not sluggish.

#### Acceptance Criteria

1. WHEN `MailFacade.list_folders` is called, THE MailFacade SHALL compute unread and total counts for all folders in a single MongoDB aggregation pipeline using `$facet` or `$group`, replacing the per-folder `count()` loop.
2. THE aggregation pipeline SHALL complete in a single database round-trip regardless of the number of folders belonging to the user.
3. WHEN the aggregation result contains no entry for a folder (zero messages), THE MailFacade SHALL return `unread_count: 0` and `total_count: 0` for that folder rather than omitting it.
4. THE System SHALL add a compound index on `(user_id, folder_id)` to `MessageDoc.Settings.indexes` if not already present, to support the aggregation efficiently.
5. WHEN `MailFacade.get_folder_counts` is called, THE MailFacade SHALL reuse the same aggregation pipeline as `list_folders` rather than issuing separate queries.
6. THE aggregation pipeline SHALL correctly handle virtual folders (`focused`, `other`, `flagged`) using the same filter logic currently applied in the per-folder loop.

### Requirement 6: Rate Limiting

**User Story:** As a system operator, I want per-user rate limits on all API endpoints, so that a single user or compromised account cannot degrade service for others.

#### Acceptance Criteria

1. THE RateLimiter SHALL enforce a configurable per-user request limit expressed as `rate_limit.requests_per_minute` (default: 300) applied across all `/api/v1/` endpoints.
2. THE RateLimiter SHALL enforce a stricter per-user limit of `rate_limit.search_requests_per_minute` (default: 30) on `GET /api/v1/search`.
3. WHEN a user exceeds the applicable rate limit, THE RateLimiter SHALL return HTTP 429 with a JSON body containing `{"error": "Rate limit exceeded", "code": "RATE_LIMITED", "retry_after_seconds": <N>}` and a `Retry-After: <N>` response header.
4. THE RateLimiter SHALL use a sliding-window counter stored in-process (using a token-bucket or sliding-window algorithm) with Redis as the backing store when `rate_limit.backend` is set to `redis`, falling back to an in-process dictionary when set to `memory`.
5. WHEN `auth.enabled` is false (dev mode), THE RateLimiter SHALL use the `dev_user_id` from settings as the rate-limit key, applying the same limits.
6. THE System SHALL add a `RateLimitConfig` sub-model to `Settings` with fields `requests_per_minute`, `search_requests_per_minute`, and `backend` (`memory` | `redis`).
7. THE RateLimiter SHALL be implemented as a FastAPI middleware and registered in `create_app()` before the `AuthMiddleware` in the middleware stack.

### Requirement 7: Field-Level Credential Encryption

**User Story:** As a system operator, I want mail account credentials stored encrypted at rest, so that a database breach does not expose OAuth tokens or POP3 passwords in plaintext.

#### Acceptance Criteria

1. WHEN an `AccountDoc` is written to MongoDB, THE System SHALL encrypt the `provider_meta` dictionary using Fernet symmetric encryption before persisting it, storing the ciphertext as a base64-encoded string in a field named `provider_meta_enc` and removing the plaintext `provider_meta` field from the stored document.
2. WHEN an `AccountDoc` is read from MongoDB, THE System SHALL decrypt `provider_meta_enc` back to a dictionary and expose it as `provider_meta` on the in-memory model, so that all existing service code continues to access credentials via `account.provider_meta` without modification.
3. THE encryption key SHALL be sourced from the environment variable `PSENSE_MAIL__SECURITY__CREDENTIAL_ENCRYPTION_KEY`, which must be a 32-byte URL-safe base64-encoded Fernet key.
4. WHEN `PSENSE_MAIL__SECURITY__CREDENTIAL_ENCRYPTION_KEY` is not set and `auth.enabled` is true, THE System SHALL raise a `ValueError` at startup with the message "CREDENTIAL_ENCRYPTION_KEY is required when auth is enabled".
5. WHEN `PSENSE_MAIL__SECURITY__CREDENTIAL_ENCRYPTION_KEY` is not set and `auth.enabled` is false (dev mode), THE System SHALL log a warning and store `provider_meta` unencrypted, preserving the current dev-mode behaviour.
6. THE `AccountDoc` model SHALL never include `provider_meta` or `provider_meta_enc` in any API response serialisation; the `accounts` router SHALL explicitly exclude these fields from all response models.
7. THE System SHALL provide a one-time migration script `scripts/encrypt_provider_meta.py` that reads all existing `AccountDoc` records with a plaintext `provider_meta` field and re-writes them with `provider_meta_enc`.

### Requirement 8: Antivirus Scanning for Attachments

**User Story:** As a user, I want uploaded attachments to be scanned for malware, so that I am not exposed to malicious files delivered via email.

#### Acceptance Criteria

1. WHEN an attachment is stored by `AttachmentFacade.upload_attachment`, THE AttachmentFacade SHALL set `av_state` to `AvState.PENDING` on the `MailAttachmentMeta` record immediately after storage.
2. WHEN `av_state` is `AvState.PENDING`, THE PreviewWorker (or a dedicated AV worker) SHALL submit the attachment bytes to the configured AV scanner adapter within 60 seconds of upload.
3. WHEN the AV scanner returns a clean result, THE System SHALL update `av_state` to `AvState.CLEAN` on the corresponding `MailAttachmentMeta` record.
4. WHEN the AV scanner returns a positive detection, THE System SHALL update `av_state` to `AvState.INFECTED`, delete the stored file from the `FileStorageAdapter`, and log a structured warning including `attachment_id`, `filename`, and `tenant_id`.
5. WHEN the AV scanner is unavailable, THE System SHALL set `av_state` to `AvState.UNKNOWN`, log a warning, and retry the scan after `workers.av_retry_interval_seconds` (default: 300).
6. WHEN a client requests download of an attachment with `av_state` of `AvState.INFECTED`, THE AttachmentFacade SHALL raise a `PolicyDeniedError` with code `ATTACHMENT_INFECTED`.
7. WHEN a client requests download of an attachment with `av_state` of `AvState.PENDING` or `AvState.UNKNOWN`, THE AttachmentFacade SHALL return the file with a response header `X-AV-State: pending` or `X-AV-State: unknown` respectively.
8. THE System SHALL define an `AVScannerAdapter` protocol in `app/adapters/protocols.py` with a single method `async def scan(self, content: bytes, filename: str) -> AVScanResult` where `AVScanResult` is a dataclass with fields `clean: bool` and `threat_name: str | None`.
9. THE System SHALL provide a `ClamAVScannerAdapter` concrete implementation and a `NoOpScannerAdapter` (always returns clean) for dev/test environments.

### Requirement 9: CORS Enforcement for Production

**User Story:** As a system operator, I want CORS to be strictly enforced in production, so that cross-origin requests from unauthorised domains are rejected.

#### Acceptance Criteria

1. WHEN `PSENSE_MAIL__APP__CORS_ORIGINS` is not explicitly set and `auth.enabled` is true, THE System SHALL raise a `ValueError` at startup with the message "CORS_ORIGINS must be explicitly configured in production".
2. WHEN `PSENSE_MAIL__APP__CORS_ORIGINS` is set to a non-empty list, THE CORSMiddleware SHALL allow only those exact origins, rejecting all others with HTTP 403.
3. WHEN `auth.enabled` is false (dev mode), THE System SHALL default `cors_origins` to `["http://localhost:3000", "http://localhost:5173"]` without requiring explicit configuration.
4. THE `AppConfig` model SHALL add a boolean field `cors_strict` (default: `false`) that, when `true`, sets `allow_credentials=True` and restricts `allow_methods` to `["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]` and `allow_headers` to `["Authorization", "Content-Type", "Idempotency-Key", "X-Correlation-ID"]`.
5. THE production Docker Compose overlay (`docker-compose.prod.yaml`) SHALL include `PSENSE_MAIL__APP__CORS_ORIGINS` and `PSENSE_MAIL__APP__CORS_STRICT=true` as required environment variables using the `${VAR:?Set VAR}` syntax.

### Requirement 10: Account ID Consistency in Data Model

**User Story:** As a developer, I want all data queries to use `account_id` as the primary scoping field, so that users with multiple mail accounts see only the correct messages per account.

#### Acceptance Criteria

1. THE MailFacade SHALL replace all `MessageDoc.user_id ==` filter expressions with `MessageDoc.account_id ==` as the primary query scope, using `account_id` derived from the authenticated user's active account context.
2. THE MailFacade SHALL replace all `ThreadDoc.user_id ==` filter expressions with `ThreadDoc.account_id ==` as the primary query scope.
3. THE MailFacade SHALL replace all `FolderDoc.user_id ==` filter expressions with `FolderDoc.account_id ==` as the primary query scope.
4. ALL other facades (ComposeFacade, SearchFacade, RulesFacade, CategoriesFacade, SignaturesFacade, TemplatesFacade, PreferencesFacade, SavedSearchesFacade) SHALL apply the same `account_id`-first scoping pattern.
5. THE `user_id` field SHALL be retained on all document models for backward compatibility and audit purposes but SHALL NOT be used as the primary filter in any new or updated query.
6. THE System SHALL add a compound index `[("account_id", 1), ("folder_id", 1), ("received_at", -1)]` to `MessageDoc.Settings.indexes` as the primary query index.
7. WHEN an API request does not supply an `account_id` context (e.g., during the migration period), THE System SHALL derive `account_id` from the user's primary account (`AccountDoc.is_primary == True`) for that `user_id`.
8. THE System SHALL provide a migration script `scripts/backfill_account_id.py` that sets `account_id` equal to `user_id` on all existing documents where `account_id` is empty or absent.

### Requirement 11: Thread Deduplication Hardening

**User Story:** As a user, I want incoming messages to be correctly grouped into threads, so that replies appear in the same conversation and unrelated messages with similar subjects are not merged.

#### Acceptance Criteria

1. THE System SHALL add a sparse index on `adapter_meta.message_id_header` to `MessageDoc.Settings.indexes` so that In-Reply-To and References header lookups in `_resolve_thread` use an index scan rather than a collection scan.
2. WHEN resolving thread membership via In-Reply-To or References headers, THE InboundPollerWorker SHALL query `MessageDoc` using the `message_id_header` index rather than the `adapter_meta` subdocument path without an index.
3. WHEN the subject+participant fallback is used, THE InboundPollerWorker SHALL limit the candidate thread scan to threads whose `last_message_at` is within the last 30 days, reducing false-positive merges for old threads with common subjects.
4. WHEN the subject+participant fallback is used and multiple candidate threads match, THE InboundPollerWorker SHALL select the thread with the most recent `last_message_at` value.
5. WHEN `inbound.subject` is empty or normalises to an empty string, THE InboundPollerWorker SHALL skip the subject+participant fallback and create a new thread immediately.
6. THE System SHALL store the RFC 2822 `Message-ID` header value in `MessageDoc.message_id_header` (the top-level field already defined on the model) rather than in `adapter_meta`, and the `_resolve_thread` lookup SHALL use this top-level field.
7. THE System SHALL add a unique sparse index on `message_id_header` to `MessageDoc.Settings.indexes` to prevent duplicate ingestion of the same RFC 2822 message.

### Requirement 12: Monotonic Op-Log Sequencing

**User Story:** As a developer, I want op-log entries to have strictly monotonic sequence numbers, so that delta sync clients can reliably consume changes in order without missing or duplicating entries.

#### Acceptance Criteria

1. THE System SHALL replace the `time.time() * 1000` default factory on `OpLogEntry.seq` with an atomic MongoDB counter using `$inc` on a dedicated `SequenceDoc` document keyed by `(tenant_id, account_id)`.
2. WHEN two `OpLogEntry` records are written concurrently for the same `(tenant_id, account_id)`, THE System SHALL guarantee that their `seq` values are distinct and strictly ordered.
3. THE `append_op` function in `app/services/op_log.py` SHALL obtain the next `seq` value by calling `SequenceDoc.find_one_and_update` with `$inc: {value: 1}` and `upsert=True` before inserting the `OpLogEntry`.
4. THE System SHALL add a `SequenceDoc` Beanie document model with fields `id` (composite key `"{tenant_id}:{account_id}"`), `value` (int, default 0), and include it in `ALL_DOCUMENTS`.
5. WHEN the `SequenceDoc` update fails (e.g., transient MongoDB error), THE `append_op` function SHALL log the error and fall back to a ULID-derived integer (the ULID timestamp component in milliseconds) rather than propagating the exception to the caller.
6. THE delta sync endpoint `GET /api/v1/sync` SHALL continue to use `seq` as the cursor value; no change to the cursor encoding is required.

### Requirement 13: Thread List Pagination

**User Story:** As a user with a large mailbox, I want the thread list to load quickly and paginate correctly, so that the application does not time out or consume excessive memory on large accounts.

#### Acceptance Criteria

1. THE `GET /api/v1/threads` endpoint SHALL accept `cursor` (opaque string), `limit` (integer, 1–200, default 50), `folder_id` (string), and `sort_order` (`asc` | `desc`, default `desc`) query parameters.
2. WHEN `cursor` is provided, THE MailFacade SHALL return only threads whose `last_message_at` is before (for `desc`) or after (for `asc`) the decoded cursor value.
3. THE response body for `GET /api/v1/threads` SHALL conform to the existing `CursorPage` schema: `{"items": [...], "next_cursor": "<opaque>|null", "total_estimate": <int>}`.
4. WHEN the result set contains more threads than `limit`, THE MailFacade SHALL set `next_cursor` to the `last_message_at` ISO 8601 timestamp of the last returned thread, base64-url encoded.
5. WHEN the result set is exhausted, THE MailFacade SHALL set `next_cursor` to `null`.
6. THE `useThread` frontend hook SHALL be extended to a `useThreads` hook that supports infinite-scroll loading via TanStack Query's `useInfiniteQuery`, fetching the next page when the user scrolls to within 200px of the bottom of the thread list.
7. THE threads router SHALL add a `GET /api/v1/threads` list endpoint (currently only `GET /api/v1/threads/{thread_id}` exists) implementing the pagination contract above.

### Requirement 14: Real-Time Push Notifications via Server-Sent Events

**User Story:** As a user, I want to be notified of new mail in real time without refreshing the page, so that I see incoming messages as soon as they arrive.

#### Acceptance Criteria

1. THE SSE_Router SHALL expose a `GET /api/v1/events` endpoint that streams Server-Sent Events to authenticated clients over a persistent HTTP connection.
2. WHEN a new `MessageDoc` is inserted by the `InboundPollerWorker`, THE System SHALL publish a `new_message` event to an in-process event bus, which THE SSE_Router SHALL forward to all connected clients belonging to the same `(tenant_id, account_id)`.
3. WHEN a `new_message` event is received by the frontend, THE QueryClient SHALL invalidate the `messages.list` and `folders.list` query caches for the affected account, triggering a background refetch.
4. THE SSE event payload for `new_message` SHALL be a JSON object with fields `type: "new_message"`, `account_id`, `folder_id`, `message_id`, and `thread_id`.
5. WHEN a client disconnects from `GET /api/v1/events`, THE SSE_Router SHALL clean up the client's subscription from the in-process event bus without error.
6. WHEN no event is published for 30 seconds, THE SSE_Router SHALL send a `comment: keepalive` line to prevent proxy timeouts.
7. THE frontend SHALL implement an `useSSE` hook in `webmail_ui/src/hooks/` that establishes the SSE connection on mount, reconnects with exponential backoff (starting at 2 seconds, capped at 60 seconds) on connection loss, and tears down the connection on unmount.
8. THE SSE_Router SHALL be registered in `create_app()` alongside the existing routers.
9. WHERE the deployment environment does not support long-lived HTTP connections, THE System SHALL document that the SSE endpoint requires a reverse proxy configured with `proxy_buffering off` (nginx) or equivalent.

### Requirement 15: Contact and Address Book Integration

**User Story:** As a user, I want to manage contacts and have the compose window auto-complete recipient addresses from my address book, so that I can address emails quickly and accurately.

#### Acceptance Criteria

1. THE System SHALL define a `ContactDoc` Beanie document model with fields: `id`, `tenant_id`, `account_id`, `user_id`, `display_name`, `emails` (list of strings), `phone_numbers` (list of strings), `company`, `notes`, `avatar_url`, `version`, `created_at`, `updated_at`, `deleted_at`, and include it in `ALL_DOCUMENTS`.
2. THE System SHALL implement a `ContactsFacade` with methods: `list_contacts`, `get_contact`, `create_contact`, `update_contact`, `delete_contact`, and `search_contacts(query: str, limit: int)`.
3. THE System SHALL expose a `contacts` router at `/api/v1/contacts` with endpoints: `GET /` (paginated list), `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}`, and `GET /search?q=<query>&limit=<n>`.
4. WHEN a user types at least 2 characters in the compose window `To:`, `Cc:`, or `Bcc:` fields, THE ComposeWindow SHALL call `GET /api/v1/contacts/search?q=<input>&limit=10` and display matching contacts as a dropdown suggestion list.
5. WHEN a user selects a contact from the suggestion list, THE ComposeWindow SHALL populate the recipient field with the contact's primary email address and display name.
6. THE contacts search endpoint SHALL return results within 200ms for mailboxes with up to 10,000 contacts, using a MongoDB text index on `display_name` and `emails`.
7. THE `ContactDoc.Settings.indexes` SHALL include a text index on `display_name` and `emails`, and a compound index on `[("account_id", 1), ("display_name", 1)]`.
8. THE contacts routes in `webmail_ui/src/routes/_app.contacts.tsx` and related components SHALL be wired to the live API, replacing the current placeholder state.

### Requirement 16: Calendar Backend — Events, iCal, and CalDAV

**User Story:** As a user, I want to create, view, and sync calendar events, so that I can manage my schedule within PSense Mail without switching to an external calendar application.

#### Acceptance Criteria

1. THE System SHALL define an `EventDoc` Beanie document model with fields: `id`, `tenant_id`, `account_id`, `user_id`, `title`, `description`, `start_at` (datetime), `end_at` (datetime), `all_day` (bool), `location`, `attendees` (list of `MailRecipient`), `recurrence_rule` (string, RFC 5545 RRULE), `ical_uid` (string), `calendar_id`, `version`, `created_at`, `updated_at`, `deleted_at`, and include it in `ALL_DOCUMENTS`.
2. THE System SHALL implement a `CalendarFacade` with methods: `list_events(account_id, start, end)`, `get_event`, `create_event`, `update_event`, `delete_event`, `import_ical(ical_bytes)`, and `export_ical(account_id, start, end)`.
3. THE System SHALL expose a `calendar` router at `/api/v1/calendar` with endpoints: `GET /events` (date-range filtered), `GET /events/{id}`, `POST /events`, `PATCH /events/{id}`, `DELETE /events/{id}`, `POST /events/import` (accepts `text/calendar` body), and `GET /events/export` (returns `text/calendar`).
4. WHEN `POST /api/v1/calendar/events/import` receives a valid iCal file, THE CalendarFacade SHALL parse all `VEVENT` components and upsert them as `EventDoc` records, matching on `ical_uid` to avoid duplicates.
5. WHEN `GET /api/v1/calendar/events/export` is called, THE CalendarFacade SHALL serialise all `EventDoc` records in the requested date range to a valid RFC 5545 iCalendar file and return it with `Content-Type: text/calendar`.
6. FOR ALL valid `EventDoc` records, parsing the exported iCal and re-importing it SHALL produce an equivalent set of `EventDoc` records (round-trip property).
7. THE calendar routes in `webmail_ui/src/routes/_app.calendar.tsx` and related components SHALL be wired to the live API, replacing the current placeholder state.
8. THE `EventDoc.Settings.indexes` SHALL include a compound index on `[("account_id", 1), ("start_at", 1), ("end_at", 1)]` to support date-range queries efficiently.

### Requirement 17: IMAP Inbound Adapter

**User Story:** As a user with an IMAP mail account, I want PSense Mail to fetch my messages via IMAP, so that I can use PSense Mail with any standard enterprise mail server.

#### Acceptance Criteria

1. THE System SHALL implement an `IMAPInboundAdapter` class in `runtime/mail_api/app/adapters/inbound/imap.py` that satisfies the `InboundAdapter` protocol.
2. THE `IMAPInboundAdapter.fetch_new_messages` method SHALL connect to the configured IMAP server using `aioimaplib`, authenticate with the provided credentials, select the `INBOX` folder, and fetch messages with UID greater than the last seen UID stored in the `SeenStore`.
3. THE `IMAPInboundAdapter` SHALL support TLS modes `ssl` (port 993), `starttls` (port 143), and `none` (port 143) via a `tls_mode` configuration field.
4. THE `IMAPInboundAdapter.acknowledge` method SHALL mark fetched messages as `\Seen` on the IMAP server rather than deleting them, preserving the original messages on the server.
5. THE `IMAPInboundAdapter.health_check` method SHALL attempt a `NOOP` command and return `AdapterHealthStatus` with `status="ok"` on success or `status="down"` with the error message in `details` on failure.
6. THE System SHALL add an `ImapConfig` sub-model to `ProviderConfig` with fields: `host`, `port`, `username`, `password`, `tls_mode`, `mailbox` (default `INBOX`), `connect_timeout_seconds` (default 10).
7. THE `AdapterRegistry.inbound` property SHALL instantiate `IMAPInboundAdapter` when `provider.active` is `imap`.
8. THE System SHALL add `aioimaplib` as a dependency in `runtime/mail_api/pyproject.toml`.

### Requirement 18: Microsoft Graph Adapter

**User Story:** As an enterprise user on Microsoft 365, I want PSense Mail to fetch and send mail via the Microsoft Graph API, so that I can use PSense Mail as my primary client without needing IMAP or POP3 access.

#### Acceptance Criteria

1. THE System SHALL implement a `MicrosoftGraphAdapter` class in `runtime/mail_api/app/adapters/inbound/msgraph.py` that satisfies the `InboundAdapter` protocol, and a corresponding `MicrosoftGraphTransportAdapter` in `runtime/mail_api/app/adapters/transport/msgraph.py` that satisfies the `TransportAdapter` protocol.
2. THE `MicrosoftGraphAdapter.fetch_new_messages` method SHALL call `GET /v1.0/me/mailFolders/inbox/messages?$filter=isRead eq false&$top=50` using the Microsoft Graph REST API, authenticated with an OAuth 2.0 access token obtained via the client credentials or delegated flow.
3. THE `MicrosoftGraphAdapter` SHALL refresh the OAuth access token automatically when it expires, using the refresh token stored in `AccountDoc.provider_meta_enc`.
4. THE `MicrosoftGraphTransportAdapter.send` method SHALL call `POST /v1.0/me/sendMail` with the message payload serialised to the Microsoft Graph message format.
5. THE System SHALL add a `MicrosoftGraphConfig` sub-model to `ProviderConfig` with fields: `tenant_id` (Azure AD tenant), `client_id`, `client_secret`, `redirect_uri`, and `scopes` (default `["Mail.ReadWrite", "Mail.Send"]`).
6. THE `AdapterRegistry` SHALL instantiate `MicrosoftGraphAdapter` and `MicrosoftGraphTransportAdapter` when `provider.active` is `msgraph`.
7. THE System SHALL add `msal` (Microsoft Authentication Library) as a dependency in `runtime/mail_api/pyproject.toml`.
8. THE `MicrosoftGraphAdapter.health_check` method SHALL call `GET /v1.0/me` and return `AdapterHealthStatus` with `status="ok"` on HTTP 200 or `status="down"` on any error.

### Requirement 19: Attachment Preview Generation

**User Story:** As a user, I want to see thumbnail previews of image and PDF attachments inline in the reading pane, so that I can quickly assess attachment content without downloading the full file.

#### Acceptance Criteria

1. WHEN an attachment is stored by `AttachmentFacade.upload_attachment` and its MIME type is `image/*` or `application/pdf`, THE System SHALL set `preview_state` to `PreviewState.PENDING` on the `MailAttachmentMeta` record.
2. THE PreviewWorker SHALL poll for `MailAttachmentMeta` records with `preview_state == PreviewState.PENDING` at an interval of `workers.preview_poll_interval_seconds` (default: 30).
3. WHEN the PreviewWorker processes an image attachment, THE PreviewWorker SHALL generate a JPEG thumbnail at 200×200 pixels maximum dimensions using Pillow, store it via the `FileStorageAdapter` at path `{user_id}/{message_id}/previews/{attachment_id}.jpg`, and set `preview_state` to `PreviewState.READY`.
4. WHEN the PreviewWorker processes a PDF attachment, THE PreviewWorker SHALL render the first page to a JPEG image at 200×200 pixels maximum dimensions using `pdf2image` (which wraps `poppler`), store it at the same path pattern, and set `preview_state` to `PreviewState.READY`.
5. WHEN preview generation fails for any reason, THE PreviewWorker SHALL set `preview_state` to `PreviewState.FAILED`, log the error with `attachment_id` and `filename`, and not retry.
6. THE `AttachmentFacade` SHALL expose a `get_preview_url(user_id, attachment_id)` method that calls `FileStorageAdapter.generate_url` for the preview path and returns the URL, raising `NotFoundError` if `preview_state` is not `PreviewState.READY`.
7. THE attachments router SHALL expose `GET /api/v1/attachments/{id}/preview` that calls `AttachmentFacade.get_preview_url` and redirects to the generated URL.
8. THE System SHALL add `Pillow` and `pdf2image` as optional dependencies in `runtime/mail_api/pyproject.toml` under an `[preview]` extras group.

### Requirement 20: GDPR Data Export Endpoint

**User Story:** As a user subject to GDPR, I want to export all my personal data from PSense Mail, so that I can exercise my right to data portability.

#### Acceptance Criteria

1. THE System SHALL expose `POST /api/v1/gdpr/export` that accepts an optional `account_id` query parameter and enqueues a data export job for the authenticated user.
2. WHEN a data export job is enqueued, THE GDPR_Exporter SHALL collect all `MessageDoc`, `ThreadDoc`, `DraftDoc`, `FolderDoc`, `ContactDoc`, `EventDoc`, `RuleDoc`, `TemplateDoc`, `SignatureDoc`, `PreferencesDoc`, and `AuditLogDoc` records belonging to the user's `(tenant_id, account_id)`.
3. THE GDPR_Exporter SHALL serialise the collected records as a ZIP archive containing one JSON file per collection (e.g., `messages.json`, `contacts.json`) and store the archive via the `FileStorageAdapter`.
4. WHEN the export archive is ready, THE System SHALL expose `GET /api/v1/gdpr/export/{job_id}` that returns the archive download URL with a 1-hour TTL, or a `{"status": "pending"}` response if the job is still running.
5. WHEN the export archive is downloaded, THE System SHALL delete the archive from storage after 24 hours.
6. THE System SHALL expose `DELETE /api/v1/gdpr/delete` that permanently hard-deletes all data for the authenticated user across all collections, returning HTTP 204 on success.
7. WHEN `DELETE /api/v1/gdpr/delete` is called, THE System SHALL require an `X-Confirm-Delete: true` request header; if absent, THE System SHALL return HTTP 400 with error code `CONFIRMATION_REQUIRED`.
8. THE System SHALL record a `AuditLogDoc` entry for every GDPR export request and every GDPR delete request, including `user_id`, `action`, `ip`, and `correlation_id`.

### Requirement 21: Structured Health Check with Adapter Aggregation

**User Story:** As a system operator, I want the `/health` endpoint to report the status of every adapter, so that monitoring systems can detect partial failures without log archaeology.

#### Acceptance Criteria

1. THE `GET /api/v1/health` endpoint SHALL call `health_check()` on every registered adapter (transport, inbound, file_storage, search) concurrently using `asyncio.gather` with a timeout of 5 seconds per adapter.
2. THE health response SHALL conform to the schema: `{"status": "ok"|"degraded"|"down", "version": "<semver>", "adapters": {"transport": {...}, "inbound": {...}, "file_storage": {...}, "search": {...}}}` where each adapter entry contains `status`, `latency_ms`, and `details`.
3. WHEN all adapters return `status="ok"`, THE health endpoint SHALL return HTTP 200 with `status="ok"`.
4. WHEN one or more adapters return `status="degraded"`, THE health endpoint SHALL return HTTP 200 with `status="degraded"`.
5. WHEN one or more adapters return `status="down"`, THE health endpoint SHALL return HTTP 503 with `status="down"`.
6. WHEN an adapter's `health_check()` call times out after 5 seconds, THE health endpoint SHALL record that adapter's status as `"down"` with `details: {"error": "timeout"}` and continue aggregating the remaining adapters.
7. THE health endpoint SHALL also report worker status: for each worker managed by `WorkerManager`, include `{"name": "<class_name>", "running": <bool>, "last_poll_at": "<iso>|null", "last_status": "<str>"}` in a `"workers"` key.
8. THE health endpoint SHALL be exempt from authentication middleware (already in `SKIP_PATHS`) and from rate limiting.

### Requirement 22: OpenTelemetry Instrumentation

**User Story:** As a system operator, I want distributed traces and metrics for all API requests and background workers, so that I can diagnose latency issues and track error rates in production.

#### Acceptance Criteria

1. THE System SHALL install `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-pymongo`, and `opentelemetry-exporter-otlp-proto-grpc` as optional dependencies in `runtime/mail_api/pyproject.toml` under an `[otel]` extras group.
2. WHEN `observability.otel_enabled` is `true` in settings, THE System SHALL initialise the OTel_SDK in the FastAPI lifespan with a `TracerProvider` and `MeterProvider` configured to export to `observability.otel_endpoint` (default: `http://localhost:4317`).
3. WHEN OTel is enabled, THE System SHALL instrument FastAPI using `FastAPIInstrumentor` so that every HTTP request generates a trace span with attributes `http.method`, `http.route`, `http.status_code`, and `tenant_id`.
4. WHEN OTel is enabled, THE System SHALL instrument MongoDB using `PymongoInstrumentor` so that every database operation generates a child span with `db.operation` and `db.collection` attributes.
5. WHEN OTel is enabled, THE System SHALL record a `psense_mail.messages_ingested` counter metric incremented by the `InboundPollerWorker` on each successful message ingestion, with attributes `account_id` and `provider`.
6. WHEN OTel is enabled, THE System SHALL record a `psense_mail.api_request_duration_ms` histogram metric for every API request, with attributes `route` and `status_code`.
7. THE System SHALL add an `ObservabilityConfig` sub-model to `Settings` with fields `otel_enabled` (bool, default `false`) and `otel_endpoint` (str, default `http://localhost:4317`).
8. WHEN `observability.otel_enabled` is `false`, THE System SHALL not import or initialise any OTel SDK components, adding zero overhead to the default configuration.

### Requirement 23: Dead-Letter Queue for Workers

**User Story:** As a system operator, I want failed worker tasks to be captured in a dead-letter queue, so that I can inspect, retry, or discard them without losing visibility into what went wrong.

#### Acceptance Criteria

1. THE System SHALL define a `DLQEntry` Beanie document model with fields: `id`, `tenant_id`, `account_id`, `worker_class` (string), `task_payload` (dict), `error_message` (string), `error_traceback` (string), `attempt_count` (int), `first_failed_at` (datetime), `last_failed_at` (datetime), and include it in `ALL_DOCUMENTS`.
2. WHEN a worker task (retry, scheduled send, snooze) exhausts `max_attempts` without success, THE WorkerManager SHALL write a `DLQEntry` record instead of only logging the failure.
3. THE System SHALL expose `GET /api/v1/admin/dlq` (admin-only) that returns a paginated list of `DLQEntry` records for the authenticated tenant, ordered by `last_failed_at` descending.
4. THE System SHALL expose `POST /api/v1/admin/dlq/{id}/retry` (admin-only) that re-enqueues the task payload for immediate processing and deletes the `DLQEntry` on success.
5. THE System SHALL expose `DELETE /api/v1/admin/dlq/{id}` (admin-only) that permanently deletes a `DLQEntry` without retrying.
6. THE `DLQEntry.Settings.indexes` SHALL include a compound index on `[("tenant_id", 1), ("last_failed_at", -1)]` and a TTL index on `last_failed_at` with a 90-day expiry.
7. WHEN a `DLQEntry` is written, THE System SHALL log a structured error at the `ERROR` level including `worker_class`, `task_payload`, `attempt_count`, and `tenant_id`.

### Requirement 24: Database Migration Tooling

**User Story:** As a developer, I want a migration framework for MongoDB schema changes, so that I can evolve the data model safely without manual intervention on production databases.

#### Acceptance Criteria

1. THE System SHALL integrate `mongrations` (or an equivalent MongoDB migration library compatible with Python 3.12 and Motor/Beanie) as a development dependency in `runtime/mail_api/pyproject.toml`.
2. THE System SHALL create a `migrations/` directory at `runtime/mail_api/migrations/` containing numbered migration scripts (e.g., `0001_add_account_id_index.py`, `0002_encrypt_provider_meta.py`).
3. WHEN `python -m migrations up` is run, THE System SHALL apply all pending migrations in ascending numeric order, recording each applied migration in a `_migrations` collection with fields `name`, `applied_at`, and `checksum`.
4. WHEN `python -m migrations down <n>` is run, THE System SHALL roll back the last `n` applied migrations in descending order, if the migration script defines a `down()` function.
5. WHEN a migration script's `up()` function raises an exception, THE System SHALL halt migration, log the error, and leave the `_migrations` collection in the state it was in before the failed migration.
6. THE System SHALL include migration scripts for: (a) adding the `message_id_header` sparse unique index to `messages`, (b) adding the `account_id` compound indexes to `messages`, `threads`, and `folders`, (c) backfilling `account_id` from `user_id` on existing documents, and (d) encrypting existing plaintext `provider_meta` fields.
7. THE `README.md` deployment checklist SHALL be updated to include a step "Run `python -m migrations up` before starting the API on any schema-changing release".

### Requirement 25: Committed OpenAPI Specification

**User Story:** As a developer, I want the OpenAPI specification committed to the repository, so that frontend type generation works in CI without requiring a running backend.

#### Acceptance Criteria

1. THE System SHALL commit the backend's OpenAPI JSON specification to `runtime/mail_api/openapi.json` and keep it up to date with every API change.
2. THE `npm run gen:api` script in `webmail_ui/package.json` SHALL be updated to read from `../runtime/mail_api/openapi.json` (relative path) instead of fetching from a running backend at `http://localhost:8000/openapi.json`.
3. THE System SHALL add a `make openapi` (or `npm run export:openapi`) command in `runtime/mail_api/` that runs `python -c "import json; from app.main import app; print(json.dumps(app.openapi()))"` and writes the output to `openapi.json`.
4. WHEN a CI pipeline runs, THE pipeline SHALL execute `make openapi` and verify that the committed `openapi.json` matches the freshly generated spec using a diff check; if they differ, THE pipeline SHALL fail with the message "openapi.json is out of date — run make openapi and commit the result".
5. THE `openapi.json` file SHALL be added to `.gitignore` exclusions (i.e., it SHALL be tracked by git, not ignored).
6. THE `README.md` developer guide SHALL be updated to document the `make openapi` command and the requirement to re-run it after any API change.

### Requirement 26: End-to-End Test Suite

**User Story:** As a developer, I want an E2E test suite covering critical user flows, so that regressions in the browser-to-API path are caught before they reach production.

#### Acceptance Criteria

1. THE System SHALL add Playwright as a development dependency in `webmail_ui/package.json` and create a `webmail_ui/e2e/` directory for E2E test files.
2. THE E2E suite SHALL include a test that: starts the backend in memory mode, navigates to the inbox, verifies that the message list renders at least one message from the seeded demo data, and opens a message to verify the reading pane displays the subject.
3. THE E2E suite SHALL include a test that: opens the compose window, fills in a recipient, subject, and body, clicks Send, and verifies that the sent message appears in the Sent folder.
4. THE E2E suite SHALL include a test that: marks a message as read, verifies the unread count in the sidebar decreases by 1, marks it unread again, and verifies the count increases by 1.
5. THE E2E suite SHALL include a test that: archives a message, verifies it disappears from the inbox, navigates to Archive, and verifies it appears there.
6. THE `webmail_ui/package.json` SHALL include an `e2e` script: `"e2e": "playwright test"` and an `e2e:ci` script: `"e2e:ci": "playwright test --reporter=github"`.
7. THE Playwright configuration SHALL use the `chromium` browser by default and set a base URL of `http://localhost:3000`.
8. THE E2E tests SHALL use the backend's memory database mode (no external MongoDB required) so they can run in CI without infrastructure dependencies.

### Requirement 27: CI/CD Pipeline Definition

**User Story:** As a developer, I want a CI/CD pipeline that runs tests and linting on every pull request, so that broken code is caught before it is merged.

#### Acceptance Criteria

1. THE System SHALL create `.github/workflows/ci.yml` defining a CI workflow triggered on `push` to any branch and `pull_request` targeting `main`.
2. THE CI workflow SHALL include a `backend` job that: checks out the repository, sets up Python 3.12, installs dependencies via `pip install -e ".[dev]"`, runs `ruff check .`, and runs `pytest --tb=short -q`.
3. THE CI workflow SHALL include a `frontend` job that: checks out the repository, sets up Node.js 20, runs `npm ci` in `webmail_ui/`, runs `npm run lint`, runs `npm run test:run`, and runs `npm run gen:api` (using the committed `openapi.json`).
4. THE CI workflow SHALL include an `openapi-check` job that: generates the OpenAPI spec from the backend and diffs it against the committed `runtime/mail_api/openapi.json`, failing if they differ.
5. THE CI workflow SHALL include an `e2e` job that: starts the backend in memory mode, starts the frontend dev server, waits for both to be healthy, and runs `npm run e2e:ci`.
6. THE CI workflow SHALL cache pip dependencies using `actions/cache` keyed on `pyproject.toml` hash, and npm dependencies using `actions/cache` keyed on `package-lock.json` hash.
7. THE System SHALL create `.github/workflows/deploy.yml` defining a CD workflow triggered on push to `main` that builds the Docker image, tags it with the git SHA, and pushes it to the configured container registry (parameterised via repository secrets).
8. THE `README.md` SHALL include a CI/CD badge linking to the GitHub Actions workflow status.

### Requirement 28: AI Copilot Surface

**User Story:** As a user, I want AI-powered email summarisation, smart reply suggestions, and priority scoring, so that I can process my inbox faster and respond more effectively.

#### Acceptance Criteria

1. THE System SHALL implement a `CopilotFacade` in `runtime/mail_api/app/services/copilot_facade.py` with methods: `summarise_message(message_id, user_id)`, `suggest_replies(message_id, user_id, count: int = 3)`, and `score_priority(message_id, user_id)`.
2. THE `CopilotFacade` SHALL depend on an `LLMAdapter` protocol defined in `app/adapters/protocols.py` with methods `async def complete(self, prompt: str, max_tokens: int) -> str` and `async def health_check() -> AdapterHealthStatus`.
3. THE System SHALL provide an `OpenAILLMAdapter` concrete implementation and a `NoOpLLMAdapter` (returns empty strings) for dev/test environments, selectable via `copilot.llm_backend` in settings (`openai` | `noop`).
4. THE System SHALL expose a `copilot` router at `/api/v1/copilot` with endpoints: `GET /messages/{id}/summary`, `GET /messages/{id}/replies`, and `GET /messages/{id}/priority`.
5. WHEN `GET /api/v1/copilot/messages/{id}/summary` is called, THE CopilotFacade SHALL return a JSON object `{"summary": "<text>"}` where the summary is at most 3 sentences.
6. WHEN `GET /api/v1/copilot/messages/{id}/replies` is called, THE CopilotFacade SHALL return a JSON object `{"suggestions": ["<reply1>", "<reply2>", "<reply3>"]}`.
7. WHEN `GET /api/v1/copilot/messages/{id}/priority` is called, THE CopilotFacade SHALL return a JSON object `{"score": <0.0–1.0>, "reason": "<text>"}`.
8. THE ReadingPane SHALL display a "Summarise" button that calls the summary endpoint and renders the result in a collapsible panel above the message body.
9. THE ComposeWindow SHALL display smart reply chips below the reading pane that, when clicked, pre-populate the compose body with the selected suggestion.
10. WHERE `copilot.llm_backend` is `noop`, THE copilot endpoints SHALL return empty/zero values without error, allowing the UI to render gracefully in dev mode.

### Requirement 29: Focused Inbox ML Scoring

**User Story:** As a user, I want the Focused Inbox to automatically classify messages as focused or other based on my engagement history, so that important messages surface without manual triage.

#### Acceptance Criteria

1. THE System SHALL implement a `FocusedInboxScorer` class in `runtime/mail_api/app/services/focused_inbox.py` that computes a focus score (0.0–1.0) for a given `MessageDoc` based on sender engagement signals.
2. THE `FocusedInboxScorer` SHALL use the following signals: (a) whether the user has previously replied to the sender (weight: 0.4), (b) whether the sender is in the user's contacts (weight: 0.3), (c) whether the user has previously opened messages from the sender (weight: 0.2), and (d) whether the message is addressed directly to the user (not CC/BCC) (weight: 0.1).
3. WHEN a new message is ingested by the `InboundPollerWorker`, THE InboundPollerWorker SHALL call `FocusedInboxScorer.score(message, user_id)` and set `MessageDoc.is_focused = True` if the score is ≥ 0.5, or `False` otherwise.
4. WHEN `PreferencesDoc.focused_inbox` is `False` for a user, THE InboundPollerWorker SHALL set `is_focused = True` for all ingested messages, effectively disabling the classifier.
5. THE `FocusedInboxScorer` SHALL query only indexed fields (`account_id`, `sender.email`, `is_read`, `folder_id`) to compute signals, avoiding collection scans.
6. THE System SHALL expose `POST /api/v1/messages/{id}/focus` and `POST /api/v1/messages/{id}/unfocus` endpoints that allow users to manually override the classifier's decision, updating `is_focused` and writing an op-log entry.
7. WHEN a user manually overrides focus classification for a sender 3 or more times, THE System SHALL record a `SenderPreferenceDoc` for that sender, and THE `FocusedInboxScorer` SHALL consult `SenderPreferenceDoc` as an override with weight 1.0 (overriding all other signals).

### Requirement 30: Offline-First Compose with Dexie Outbox

**User Story:** As a user on a flaky connection, I want to compose and queue emails for sending even when offline, so that my messages are delivered as soon as connectivity is restored.

#### Acceptance Criteria

1. WHEN a user clicks Send in the ComposeWindow and the API is unreachable (network error or HTTP 5xx), THE ComposeWindow SHALL write the draft payload to a Dexie `outbox` table with status `queued` and display a toast notification reading "Message queued — will send when online".
2. WHEN the browser comes back online (via the `navigator.onLine` event or a successful API health probe), THE System SHALL drain the Dexie `outbox` by calling `POST /api/v1/drafts/{id}/send` for each queued item in insertion order.
3. WHEN an outbox item is sent successfully, THE System SHALL delete it from the Dexie `outbox` table and invalidate the sent folder query cache.
4. WHEN an outbox item fails to send after 3 attempts, THE System SHALL set its status to `failed` and display a persistent toast notification with a "Retry" action.
5. THE Dexie `outbox` table SHALL have the schema: `id` (string, primary key), `draft_payload` (object), `status` (`queued` | `sending` | `failed`), `attempt_count` (number), `queued_at` (Date), `last_attempted_at` (Date | null).
6. THE System SHALL implement an `OutboxDrainer` class in `webmail_ui/src/lib/sync/outbox-drainer.ts` that is instantiated once in the `__root.tsx` provider tree and manages the drain lifecycle.
7. WHEN the application loads and the `outbox` table contains items with status `queued`, THE OutboxDrainer SHALL begin draining immediately if the network is available.
8. THE ComposeWindow SHALL display a badge on the send button showing the count of queued outbox items when the count is greater than 0.

### Requirement 31: Webhook and Event Bus for Integrations

**User Story:** As an enterprise administrator, I want to register webhooks that receive PSense Mail events, so that I can pipe mail activity into Slack, Zapier, or internal systems without polling the API.

#### Acceptance Criteria

1. THE System SHALL define a `WebhookSubscriptionDoc` Beanie document model with fields: `id`, `tenant_id`, `account_id`, `url` (string, HTTPS only), `events` (list of strings, e.g., `["message.received", "message.sent", "rule.triggered"]`), `secret` (string, used for HMAC-SHA256 signature), `enabled` (bool), `version`, `created_at`, `updated_at`, `deleted_at`, and include it in `ALL_DOCUMENTS`.
2. THE System SHALL implement an `EventBusFacade` in `runtime/mail_api/app/services/event_bus_facade.py` with a method `async def publish(event_type: str, payload: dict, tenant_id: str, account_id: str)` that looks up all enabled `WebhookSubscriptionDoc` records matching the event type and enqueues delivery tasks.
3. THE System SHALL expose a `webhooks` router at `/api/v1/webhooks` with endpoints: `GET /` (list subscriptions), `POST /` (create subscription), `PATCH /{id}`, `DELETE /{id}`, and `POST /{id}/test` (sends a test ping event).
4. WHEN `EventBusFacade.publish` is called, THE System SHALL deliver the event payload to each matching subscriber URL via an HTTP POST with a JSON body `{"event": "<type>", "payload": {...}, "timestamp": "<iso>"}` and a `X-PSense-Signature: sha256=<hmac>` header computed using the subscription's `secret`.
5. WHEN a webhook delivery fails (non-2xx response or network error), THE System SHALL retry up to 3 times with exponential backoff (30s, 300s, 3000s) before writing a `DLQEntry`.
6. WHEN `POST /api/v1/webhooks/{id}/test` is called, THE System SHALL deliver a `{"event": "ping", "payload": {}}` payload to the subscription URL and return `{"delivered": true, "status_code": <n>}` or `{"delivered": false, "error": "<msg>"}`.
7. THE `WebhookSubscriptionDoc.url` field SHALL be validated to require HTTPS scheme; HTTP URLs SHALL be rejected with a `ValidationError`.
8. THE `EventBusFacade.publish` method SHALL be called by the `InboundPollerWorker` on `message.received`, by the `ComposeFacade` on `message.sent`, and by the `RulesFacade` on `rule.triggered`.
9. THE `WebhookSubscriptionDoc.Settings.indexes` SHALL include a compound index on `[("tenant_id", 1), ("events", 1), ("enabled", 1)]` to support efficient event-type lookups.
