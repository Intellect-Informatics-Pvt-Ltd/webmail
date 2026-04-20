# Requirements Document

## Introduction

PSense Mail Gap Remediation addresses 31 identified gaps across the PSense Mail enterprise webmail workspace. The system is built on FastAPI + Python 3.12 + MongoDB (Beanie ODM) on the backend and React 19 + TanStack Start + TanStack Query v5 + Dexie v4 on the frontend. This remediation covers critical blockers (P0), security hardening (P1), data model correctness (P1), missing product features (P2–P3), observability and operations (P2–P3), developer experience (P3), and strategic enhancements.

Requirements are organized by priority tier. Each requirement carries acceptance criteria written in EARS notation and correctness properties suitable for property-based testing where applicable.

---

## Glossary

- **API_Client**: The TypeScript fetch wrapper at `src/lib/api/client.ts` that injects auth headers, correlation IDs, and idempotency keys.
- **TanStack_Query**: The server-state cache layer (TanStack Query v5) used for all server data in the frontend.
- **Dexie**: The IndexedDB wrapper (Dexie v4) used as the TanStack Query persister, outbox, op-log, and attachment blob store.
- **Sanitizer**: The HTML sanitization component responsible for stripping XSS vectors from inbound message bodies before rendering.
- **JWKS_Cache**: The in-process cache for JSON Web Key Sets fetched from the KeyCloak JWKS endpoint.
- **Poller_Dispatcher**: The backend component that manages one `InboundPollerWorker` per active mail account.
- **MailFacade**: The backend service facade at `app/services/mail_facade.py` providing core mail operations.
- **AdapterRegistry**: The configuration-driven factory at `app/adapters/registry.py` that selects concrete adapter implementations.
- **OpLog**: The append-only change-feed collection (`op_log`) used for delta sync between server and client.
- **Seq_Generator**: The component responsible for producing strictly monotonic sequence numbers for `OpLogEntry.seq`.
- **Rate_Limiter**: The middleware component enforcing per-user and per-tenant request rate limits.
- **Credential_Encryptor**: The component that applies Fernet symmetric encryption to `AccountDoc.provider_meta` fields before persistence.
- **AV_Scanner**: The antivirus scanning integration called during attachment upload.
- **SSE_Stream**: The Server-Sent Events endpoint that pushes op-log entries to connected clients in real time.
- **ContactDoc**: The MongoDB document model representing a contact in the address book.
- **EventDoc**: The MongoDB document model representing a calendar event.
- **IMAP_Adapter**: The inbound adapter implementing the `InboundAdapter` protocol for IMAP servers.
- **Graph_Adapter**: The inbound and transport adapter implementing both `InboundAdapter` and `TransportAdapter` protocols for Microsoft Graph API.
- **Preview_Worker**: The background worker that generates thumbnail and PDF previews for attachments.
- **DLQ**: The dead-letter queue that receives jobs after all retry attempts are exhausted.
- **Migration_Runner**: The tooling component that applies ordered, idempotent schema migrations to MongoDB collections.
- **Copilot_Facade**: The backend service facade providing AI-powered summarization, smart reply, and priority scoring.
- **Outbox**: The Dexie table storing pending outbound drafts for offline-first compose.
- **Webhook_Dispatcher**: The background worker that delivers mail events to registered external webhook endpoints.
- **Health_Aggregator**: The component that collects `AdapterHealthStatus` from all registered adapters and computes an overall system health status.
- **OpenTelemetry_Provider**: The OpenTelemetry SDK configuration that instruments FastAPI routes, facade methods, and worker loops with traces and metrics.
- **GDPR_Exporter**: The backend service that assembles a complete, portable data export for a given user.
- **Focused_Scorer**: The ML scoring component that assigns a `focused_score` float in [0.0, 1.0] to each inbound message.

