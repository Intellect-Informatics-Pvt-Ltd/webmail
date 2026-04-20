# Design Document — PSense Mail Hardening

## Overview

PSense Mail Hardening addresses 31 identified gaps across seven categories: critical functional gaps, security hardening, data model correctness, missing product features, observability and operations, developer experience, and strategic enhancements. All changes are additive or backward-compatible migrations; no existing API contracts are broken without a versioned transition path.

The system is a FastAPI backend (Python 3.12, Beanie/Motor, MongoDB) paired with a React 19 frontend (TanStack Start, TanStack Query v5, Dexie, Zustand). The adapter registry pattern already in place is extended to cover new concerns (LLM, AV scanning, IMAP, Microsoft Graph). All new backend services follow the existing facade pattern. All new frontend state follows the existing TanStack Query + Dexie pattern.

### Guiding Principles

1. **Adapter-first**: every external dependency (LLM, AV scanner, IMAP, MS Graph) is hidden behind a protocol so the memory/noop adapter can be used in tests and dev mode.
2. **Backward-compatible migration**: `user_id` is retained on all documents; `account_id` becomes the primary query field via a backfill script and index additions.
3. **Fail-safe defaults**: encryption key absence in dev mode logs a warning; in production it raises at startup. CORS misconfiguration raises at startup in production.
4. **Single round-trip aggregations**: N+1 query patterns are replaced with `$facet` pipelines; new indexes are added before the queries that use them.
5. **In-process first**: SSE event bus, rate limiter (memory backend), and JWKS cache are in-process singletons. Redis backends are opt-in via config.

