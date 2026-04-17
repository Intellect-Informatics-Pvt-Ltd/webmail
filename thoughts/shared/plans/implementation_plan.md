# PSense Mail — Python API Façade Backend

## Goal

Build a **production-grade, configuration-driven Python FastAPI backend** for PSense Mail that provides a complete API surface matching every operation the webmail UI currently performs (via Zustand stores), while remaining **provider-agnostic** — swappable between Gmail API, MailPit (local dev / org SMTP), and future providers (Microsoft Graph, generic IMAP) via YAML configuration. Authentication is delegated to **KeyCloak** (integrated later as a middleware layer).

---

## Background & Context

### Current State
The webmail UI (TanStack Start + React 19) runs 100% client-side with Zustand + localStorage. Three stores drive all functionality:

| Store | Persisted Key | Operations |
|-------|---------------|------------|
| `mail-store` | `psense-mail-data` | Messages CRUD, folder management, rules, templates, signatures, categorization, flagging, pinning, snoozing, archiving, deletion, move |
| `compose-store` | `psense-compose` | Draft lifecycle (create/update/save/discard), compose window state |
| `ui-store` | per-key prefs | Preferences (density, reading pane, theme, sort, notifications, OOO, shortcuts) |

### Existing Specs
- [mail_backend_facade_spec.md](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/thoughts/shared/plans/mail_backend_facade_spec.md) — High-level façade contract
- [mail_facade_reference.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/thoughts/shared/plans/mail_facade_reference.py) — Pydantic models + Protocol definitions

### What This Plan Adds
1. **Configuration-driven provider system** — YAML config selects Gmail, MailPit, or in-memory adapter
2. **Complete API coverage** — Every UI operation mapped to a REST endpoint
3. **KeyCloak auth readiness** — Middleware stub with JWT validation hook
4. **Missing domains** — Categories, Favorites, Saved Searches, Preferences (not in original spec)
5. **Production concerns** — Structured logging, health checks, correlation IDs, rate limiting, CORS

---

## User Review Required

> [!IMPORTANT]
> **Provider Priority**: This plan implements **MailPit** first (for local dev) and **Gmail API** second. Microsoft Graph is designed-for but not implemented in Phase 1. Please confirm this priority.

> [!IMPORTANT]
> **Database**: The plan uses **PostgreSQL** (via async SQLAlchemy + Alembic) for persistent storage of messages, folders, rules, templates, signatures, preferences, and categories. The mail provider adapters handle send/receive; the DB is the system of record for UI state. Is this acceptable, or should we start with a simpler SQLite option for dev?

> [!IMPORTANT]
> **KeyCloak Integration**: Auth is stubbed as middleware that extracts `user_id` from JWT claims. The actual KeyCloak server provisioning and OIDC config are deferred. The backend will ship with a dev-mode bypass (`AUTH_DISABLED=true`) for local testing. Confirm this approach.

> [!WARNING]
> **Attachment Storage**: The plan uses local filesystem storage for dev (with a configurable path) and an S3-compatible adapter interface for production. File uploads go through the API, not direct-to-storage signed URLs (that optimization is future work).

---

## Proposed Changes

The backend lives entirely under `runtime/mail_api/`. The webmail UI is **not modified** in this phase — the API is built to be a drop-in replacement for the Zustand stores when the frontend is ready to integrate (via TanStack Query hooks).

---

### Component 1: Project Skeleton & Configuration

#### [NEW] [runtime/mail_api/](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/)

```
runtime/mail_api/
├── pyproject.toml              # Project metadata, dependencies (FastAPI, uvicorn, SQLAlchemy, etc.)
├── config/
│   ├── settings.py             # Pydantic Settings model (env + YAML merge)
│   ├── default.yaml            # Default configuration
│   ├── providers/
│   │   ├── mailpit.yaml        # MailPit adapter config
│   │   └── gmail.yaml          # Gmail API adapter config
│   └── logging.yaml            # Structured logging config
├── alembic/                    # DB migrations
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory, lifespan, middleware
│   ├── dependencies.py         # FastAPI Depends: get_db, get_current_user, get_facade
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py             # KeyCloak JWT middleware (with dev bypass)
│   │   ├── correlation.py      # X-Correlation-ID injection
│   │   └── error_handler.py    # Domain exception → HTTP response mapper
│   ├── api/                    # HTTP layer (thin — delegates to services)
│   │   ├── __init__.py
│   │   └── routers/
│   │       ├── mailbox.py      # Folders, favorites
│   │       ├── messages.py     # List, get, actions (bulk)
│   │       ├── threads.py      # Thread-level operations
│   │       ├── drafts.py       # Draft lifecycle + send
│   │       ├── search.py       # Search + suggestions
│   │       ├── attachments.py  # Upload/download
│   │       ├── rules.py        # Mail rules CRUD
│   │       ├── templates.py    # Templates CRUD
│   │       ├── signatures.py   # Signatures CRUD
│   │       ├── categories.py   # Categories CRUD
│   │       ├── preferences.py  # User preferences
│   │       ├── saved_searches.py  # Saved searches CRUD
│   │       └── admin.py        # Health, seed, diagnostics
│   ├── domain/                 # Pure domain — no framework imports
│   │   ├── __init__.py
│   │   ├── enums.py            # DeliveryState, FolderKind, Importance, MessageAction
│   │   ├── errors.py           # MailDomainError hierarchy
│   │   ├── models.py           # Pydantic domain models
│   │   ├── requests.py         # Request DTOs
│   │   └── responses.py        # Response DTOs + pagination
│   ├── services/               # Business logic façades
│   │   ├── __init__.py
│   │   ├── mail_facade.py      # MailFacade implementation
│   │   ├── compose_facade.py   # ComposeFacade implementation
│   │   ├── search_facade.py    # SearchFacade implementation
│   │   ├── attachment_facade.py
│   │   ├── rules_facade.py     # Rules CRUD + evaluation engine
│   │   ├── templates_facade.py
│   │   ├── signatures_facade.py
│   │   ├── categories_facade.py
│   │   ├── preferences_facade.py
│   │   ├── saved_searches_facade.py
│   │   └── admin_facade.py
│   ├── adapters/               # Provider implementations (config-selected)
│   │   ├── __init__.py
│   │   ├── registry.py         # AdapterRegistry — loads adapters from config
│   │   ├── protocols.py        # Abstract base protocols for all adapters
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── postgres.py     # SQLAlchemy async repository
│   │   │   └── models.py       # SQLAlchemy ORM models
│   │   ├── transport/
│   │   │   ├── __init__.py
│   │   │   ├── mailpit.py      # MailPit SMTP adapter
│   │   │   ├── gmail.py        # Gmail API adapter
│   │   │   └── memory.py       # In-memory (unit tests)
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   ├── postgres.py     # Full-text search via pg_trgm + tsvector
│   │   │   └── memory.py       # In-memory search (tests)
│   │   ├── inbound/
│   │   │   ├── __init__.py
│   │   │   ├── mailpit.py      # MailPit webhook/poll receiver
│   │   │   └── gmail.py        # Gmail push notification handler
│   │   └── file_storage/
│   │       ├── __init__.py
│   │       ├── local.py        # Local filesystem
│   │       └── s3.py           # S3-compatible (future)
│   ├── workers/                # Background task runners
│   │   ├── __init__.py
│   │   ├── send_worker.py      # Async send queue processor
│   │   ├── snooze_worker.py    # Snooze wake-up scheduler
│   │   ├── rule_worker.py      # Rule evaluation on inbound
│   │   └── sync_worker.py      # Provider mailbox sync (Gmail)
│   └── seed/
│       ├── __init__.py
│       └── demo_data.py        # Port of webmail_ui/src/data/* to seed DB
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_mail_facade.py
│   │   ├── test_compose_facade.py
│   │   ├── test_search_facade.py
│   │   └── test_rules_engine.py
│   └── integration/
│       ├── test_message_api.py
│       ├── test_draft_api.py
│       └── test_mailpit_transport.py
├── Dockerfile
├── docker-compose.yaml         # Postgres + MailPit + API
└── README.md
```

---

### Component 2: Configuration System

#### [NEW] [default.yaml](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/config/default.yaml)

Configuration-driven design. Environment variables override YAML. Provider selection is a single key.

```yaml
app:
  name: "PSense Mail API"
  version: "0.1.0"
  debug: false
  cors_origins: ["http://localhost:3000"]

auth:
  enabled: false                    # Set true when KeyCloak is ready
  issuer: "https://auth.psense.ai/realms/psense"
  audience: "psense-mail-api"
  jwks_uri: "https://auth.psense.ai/realms/psense/protocol/openid-connect/certs"
  dev_user_id: "dev-user-001"      # Used when auth.enabled = false

database:
  url: "postgresql+asyncpg://psense:psense@localhost:5432/psense_mail"
  pool_size: 10
  echo: false

provider:
  active: "mailpit"                # "mailpit" | "gmail" | "memory"

  mailpit:
    smtp_host: "localhost"
    smtp_port: 1025
    api_url: "http://localhost:8025"
    from_address: "noreply@psense.local"

  gmail:
    credentials_file: "/secrets/gmail-credentials.json"
    token_file: "/secrets/gmail-token.json"
    scopes:
      - "https://www.googleapis.com/auth/gmail.modify"
      - "https://www.googleapis.com/auth/gmail.send"
    watch_topic: "projects/psense-mail/topics/gmail-push"

storage:
  backend: "local"                 # "local" | "s3"
  local:
    base_path: "./data/attachments"
  s3:
    bucket: "psense-mail-attachments"
    region: "us-east-1"
    endpoint_url: null

search:
  backend: "postgres"             # "postgres" | "memory"

workers:
  enabled: true
  snooze_check_interval_seconds: 60
  send_retry_max_attempts: 3
  sync_interval_seconds: 300      # Gmail sync poll fallback

logging:
  level: "INFO"
  format: "json"
  correlation_header: "X-Correlation-ID"
```

#### [NEW] [settings.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/config/settings.py)

Pydantic Settings model that merges YAML + environment variables. Supports `PSENSE_MAIL__PROVIDER__ACTIVE=gmail` style overrides.

---

### Component 3: Domain Layer

All data contracts derived from the webmail UI's `types/mail.ts` + the existing `mail_facade_reference.py`, extended with fields the UI consumes but the reference didn't model.

#### [NEW] [enums.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/domain/enums.py)

```python
# DeliveryState, FolderKind (from reference)
# + Importance (low | normal | high)
# + MessageAction (archive | delete | restore | move | mark_read | mark_unread |
#                  flag | unflag | pin | unpin | snooze | unsnooze |
#                  categorize | uncategorize)
# + RuleConditionField (sender | subject | hasAttachment | olderThanDays)
# + RuleActionType (move | categorize | markImportant | archive | delete)
# + Density, ReadingPanePlacement, Theme, DefaultSort, DefaultReply
```

#### [NEW] [models.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/domain/models.py)

Complete domain models matching every type in `webmail_ui/src/types/mail.ts`:

| UI Type | Python Model | Notes |
|---------|-------------|-------|
| `MailRecipient` | `MailRecipient` | + `avatar_color` field |
| `MailAttachment` | `MailAttachment` | + `content_id`, `checksum`, `adapter_meta` |
| `MailCategory` | `MailCategory` | + user-scoped |
| `MailFolder` | `MailFolder` | + `kind`, `unread_count`, `total_count`, `sort_order` |
| `MailMessage` | `MailMessage` | Full field parity with TS type |
| `MailThread` | `MailThread` | + `messages` list for thread view |
| `MailRule` | `MailRule` | Conditions + actions as typed unions |
| `MailTemplate` | `MailTemplate` | Subject + bodyHtml |
| `MailSignature` | `MailSignature` | + `is_default` |
| `SavedSearch` | `SavedSearch` | Query + filters dict |
| `ComposeDraft` | `ComposeDraft` | Full draft state |
| `UserPreferences` | `UserPreferences` | All prefs from UI store |

#### [NEW] [errors.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/domain/errors.py)

Full exception hierarchy from reference + `AuthenticationError`, `AuthorizationError`.

---

### Component 4: Service Façades — Complete API Surface

Every Zustand store action maps to a façade method. Here is the **complete operation mapping**:

#### MailFacade ([mail_facade.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/services/mail_facade.py))

| UI Store Action | Façade Method | HTTP Route |
|-----------------|---------------|------------|
| (read) messages by folder | `list_messages(user_id, folder_id, query)` | `GET /api/v1/messages?folder_id=&cursor=&limit=` |
| (read) message detail | `get_message(user_id, message_id)` | `GET /api/v1/messages/{id}` |
| (read) thread detail | `get_thread(user_id, thread_id)` | `GET /api/v1/threads/{id}` |
| `toggleRead(ids, read?)` | `apply_action(ids, "mark_read"/"mark_unread")` | `POST /api/v1/messages/actions` |
| `toggleFlag(ids)` | `apply_action(ids, "flag"/"unflag")` | `POST /api/v1/messages/actions` |
| `togglePin(ids)` | `apply_action(ids, "pin"/"unpin")` | `POST /api/v1/messages/actions` |
| `moveTo(ids, folderId)` | `apply_action(ids, "move", dest=folderId)` | `POST /api/v1/messages/actions` |
| `archive(ids)` | `apply_action(ids, "archive")` | `POST /api/v1/messages/actions` |
| `remove(ids)` | `apply_action(ids, "delete")` | `POST /api/v1/messages/actions` |
| `snooze(ids, until)` | `apply_action(ids, "snooze", snooze_until=...)` | `POST /api/v1/messages/actions` |
| `categorize(ids, catId)` | `apply_action(ids, "categorize", category_ids=[...])` | `POST /api/v1/messages/actions` |
| `upsertMessage(m)` | `upsert_message(user_id, message)` | `PUT /api/v1/messages/{id}` |
| (folder unread counts) | `get_folder_counts(user_id)` | `GET /api/v1/folders/counts` |

#### Folder & Favorite Façade (part of MailFacade)

| UI Store Action | Façade Method | HTTP Route |
|-----------------|---------------|------------|
| (read) folders | `list_folders(user_id)` | `GET /api/v1/folders` |
| `addFolder(name)` | `create_folder(user_id, name)` | `POST /api/v1/folders` |
| `renameFolder(id, name)` | `rename_folder(user_id, id, name)` | `PATCH /api/v1/folders/{id}` |
| `deleteFolder(id)` | `delete_folder(user_id, id)` | `DELETE /api/v1/folders/{id}` |
| `toggleFavorite(folderId)` | `toggle_favorite(user_id, folder_id)` | `POST /api/v1/folders/{id}/favorite` |
| (read) favorites | `list_favorites(user_id)` | `GET /api/v1/folders/favorites` |

#### ComposeFacade ([compose_facade.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/services/compose_facade.py))

| UI Store Action | Façade Method | HTTP Route |
|-----------------|---------------|------------|
| `openCompose(init?)` | `create_draft(user_id, payload)` | `POST /api/v1/drafts` |
| `updateOpen(patch)` | `update_draft(user_id, draft_id, patch)` | `PATCH /api/v1/drafts/{id}` |
| `saveDraft()` | `save_draft(user_id, draft_id)` | `POST /api/v1/drafts/{id}/save` |
| `discardDraft(id?)` | `discard_draft(user_id, draft_id)` | `DELETE /api/v1/drafts/{id}` |
| (send) | `send_draft(user_id, draft_id, request)` | `POST /api/v1/drafts/{id}/send` |
| (retry) | `retry_send(user_id, message_id)` | `POST /api/v1/messages/{id}/retry` |
| (list drafts) | `list_drafts(user_id)` | `GET /api/v1/drafts` |

#### SearchFacade ([search_facade.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/services/search_facade.py))

Maps the `use-filtered-messages.ts` filter logic + search syntax (`from:`, `has:attachment`, `is:unread`, `subject:`, `to:`) to server-side query.

| Operation | Façade Method | HTTP Route |
|-----------|---------------|------------|
| Full-text search | `search_messages(user_id, request)` | `POST /api/v1/search/messages` |
| Suggestions | `get_suggestions(user_id, partial)` | `GET /api/v1/search/suggest?q=` |
| Faceted results | Included in search response | (same endpoint) |

#### RulesFacade ([rules_facade.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/services/rules_facade.py))

| UI Store Action | Façade Method | HTTP Route |
|-----------------|---------------|------------|
| (read) rules | `list_rules(user_id)` | `GET /api/v1/rules` |
| `addRule(rule)` | `create_rule(user_id, rule)` | `POST /api/v1/rules` |
| `updateRule(rule)` | `update_rule(user_id, rule_id, rule)` | `PUT /api/v1/rules/{id}` |
| `deleteRule(id)` | `delete_rule(user_id, rule_id)` | `DELETE /api/v1/rules/{id}` |
| (evaluate on inbound) | `evaluate_rules(user_id, message)` | Internal (worker) |

#### TemplatesFacade, SignaturesFacade, CategoriesFacade, SavedSearchesFacade

Standard CRUD pattern for each:

| Resource | Routes |
|----------|--------|
| Templates | `GET/POST /api/v1/templates`, `PUT/DELETE /api/v1/templates/{id}` |
| Signatures | `GET/POST /api/v1/signatures`, `PUT/DELETE /api/v1/signatures/{id}`, `POST /api/v1/signatures/{id}/default` |
| Categories | `GET/POST /api/v1/categories`, `PUT/DELETE /api/v1/categories/{id}` |
| Saved Searches | `GET/POST /api/v1/saved-searches`, `DELETE /api/v1/saved-searches/{id}` |

#### PreferencesFacade ([preferences_facade.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/services/preferences_facade.py))

| UI Store Action | Façade Method | HTTP Route |
|-----------------|---------------|------------|
| (read) prefs | `get_preferences(user_id)` | `GET /api/v1/preferences` |
| `setDensity/setReadingPane/setTheme/patch` | `update_preferences(user_id, patch)` | `PATCH /api/v1/preferences` |

#### AdminFacade ([admin_facade.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/services/admin_facade.py))

| Operation | Façade Method | HTTP Route |
|-----------|---------------|------------|
| Health | `get_health()` | `GET /api/v1/health` |
| Seed demo | `seed_demo(user_id, scenario)` | `POST /api/v1/admin/seed` |
| Replay failed | `replay_failed_sends(user_id)` | `POST /api/v1/admin/replay-sends` |
| Diagnostics | `get_diagnostics()` | `GET /api/v1/admin/diagnostics` |

---

### Component 5: Adapter Layer — Provider Abstraction

#### [NEW] [protocols.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/adapters/protocols.py)

```python
class TransportAdapter(Protocol):
    """Send outbound mail."""
    async def send(self, message: OutboundMessage) -> TransportReceipt: ...
    async def health_check(self) -> AdapterHealthStatus: ...

class InboundAdapter(Protocol):
    """Receive inbound mail from provider."""
    async def fetch_new_messages(self, mailbox_id: str, since: datetime | None) -> list[InboundMessage]: ...
    async def acknowledge(self, message_ids: list[str]) -> None: ...

class FileStorageAdapter(Protocol):
    """Store and retrieve attachment files."""
    async def store(self, path: str, content: bytes, content_type: str) -> str: ...
    async def retrieve(self, path: str) -> tuple[bytes, str]: ...
    async def delete(self, path: str) -> None: ...
    async def generate_url(self, path: str, ttl_seconds: int = 300) -> str: ...

class SearchAdapter(Protocol):
    """Full-text search indexing and querying."""
    async def index_message(self, message: MailMessage) -> None: ...
    async def search(self, user_id: str, request: SearchRequest) -> SearchResponse: ...
    async def suggest(self, user_id: str, partial: str) -> list[str]: ...
```

#### [NEW] [registry.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/adapters/registry.py)

```python
class AdapterRegistry:
    """Configuration-driven adapter factory.
    
    Reads `provider.active` from settings and instantiates the correct
    transport, inbound, storage, and search adapters.
    """
    def __init__(self, settings: Settings): ...
    
    @cached_property
    def transport(self) -> TransportAdapter: ...
    
    @cached_property
    def inbound(self) -> InboundAdapter: ...
    
    @cached_property
    def file_storage(self) -> FileStorageAdapter: ...
    
    @cached_property
    def search(self) -> SearchAdapter: ...
```

#### Provider: MailPit

| Adapter | Implementation |
|---------|---------------|
| Transport | SMTP via `aiosmtplib` to MailPit (port 1025) |
| Inbound | MailPit REST API polling (`GET /api/v1/messages`) |
| File Storage | Local filesystem |
| Search | PostgreSQL `tsvector` + `pg_trgm` |

#### Provider: Gmail

| Adapter | Implementation |
|---------|---------------|
| Transport | Gmail API `messages.send` via `google-api-python-client` |
| Inbound | Gmail API `messages.list` + Cloud Pub/Sub push notifications |
| File Storage | Local filesystem (attachments extracted from messages) |
| Search | PostgreSQL (local index) — Gmail search is supplementary |

---

### Component 6: Database Layer

#### ORM Models ([storage/models.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/adapters/storage/models.py))

Maps the schema from `04-backend-architecture.md` to SQLAlchemy async models:

| Table | Key Fields |
|-------|------------|
| `users` | `id`, `email`, `display_name`, `avatar_url` (populated from KeyCloak) |
| `folders` | `id`, `user_id`, `name`, `kind`, `system`, `parent_id`, `sort_order` |
| `categories` | `id`, `user_id`, `name`, `color` |
| `messages` | Full MailMessage fields + `version` for optimistic concurrency |
| `threads` | `id`, `user_id`, `subject`, `last_message_at`, `unread_count`, `folder_id` |
| `attachments` | `id`, `message_id`, `user_id`, `name`, `size`, `mime`, `storage_path` |
| `rules` | `id`, `user_id`, `name`, `enabled`, `conditions` (JSONB), `actions` (JSONB) |
| `templates` | `id`, `user_id`, `name`, `subject`, `body_html` |
| `signatures` | `id`, `user_id`, `name`, `body_html`, `is_default` |
| `drafts` | `id`, `user_id`, full draft state + `delivery_state` |
| `user_preferences` | One row per user, mirrors `UserPreferences` type |
| `saved_searches` | `id`, `user_id`, `name`, `query`, `filters` (JSONB) |
| `favorites` | `user_id`, `folder_id` (junction table) |
| `delivery_log` | `id`, `message_id`, `state`, `transport_message_id`, `diagnostic`, `timestamp` |

---

### Component 7: Auth Middleware (KeyCloak-Ready)

#### [NEW] [auth.py](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/app/middleware/auth.py)

```python
class AuthMiddleware:
    """KeyCloak JWT validation middleware.
    
    When auth.enabled = false (dev mode):
        - Injects auth.dev_user_id into request state
        
    When auth.enabled = true:
        - Validates Bearer token against KeyCloak JWKS
        - Extracts user_id, email, roles from JWT claims
        - Rejects with 401 on invalid/expired tokens
        - Supports token refresh via KeyCloak standard flow
    """
```

Dependencies inject the authenticated user:

```python
async def get_current_user(request: Request) -> AuthenticatedUser:
    """Extract user from request state (set by AuthMiddleware)."""
```

---

### Component 8: Workers (Background Tasks)

| Worker | Purpose | Schedule |
|--------|---------|----------|
| `send_worker` | Process send queue, retry failed deliveries | Event-driven (on draft send) |
| `snooze_worker` | Move snoozed messages back to inbox when `snoozed_until <= now()` | Every 60s |
| `rule_worker` | Evaluate user rules against new inbound messages | On inbound message event |
| `sync_worker` | Pull new messages from Gmail/MailPit | Every 5 min (configurable) |

Workers use `asyncio.create_task` within the FastAPI lifespan for simplicity (Phase 1). A proper task queue (Celery/ARQ) is a future upgrade.

---

### Component 9: Docker Compose (Local Dev)

#### [NEW] [docker-compose.yaml](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/runtime/mail_api/docker-compose.yaml)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: psense_mail
      POSTGRES_USER: psense
      POSTGRES_PASSWORD: psense
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  mailpit:
    image: axllent/mailpit:latest
    ports:
      - "1025:1025"    # SMTP
      - "8025:8025"    # Web UI + REST API

  api:
    build: .
    ports: ["8000:8000"]
    environment:
      PSENSE_MAIL__DATABASE__URL: "postgresql+asyncpg://psense:psense@postgres:5432/psense_mail"
      PSENSE_MAIL__PROVIDER__ACTIVE: "mailpit"
      PSENSE_MAIL__PROVIDER__MAILPIT__SMTP_HOST: "mailpit"
      PSENSE_MAIL__PROVIDER__MAILPIT__API_URL: "http://mailpit:8025"
    depends_on: [postgres, mailpit]

volumes:
  pgdata:
```

---

### Component 10: BRD Enhancement

#### [MODIFY] [01-brd.md](file:///Users/narayanaa/DevCode/Srikari/psense-services/web-mail/thoughts/shared/plans/01-brd.md)

Updates to the BRD:

1. **Section 4 (In scope v1)** — Add: "Python FastAPI backend with configuration-driven provider selection (MailPit for dev, Gmail API for production)"
2. **Section 5 (Out of scope)** — Revise: Move "Real mail provider integration" from v2 to v1.1 with MailPit + Gmail
3. **Section 8 (Risks)** — Add: "Gmail API rate limits (250 units/sec per user) may require batching for bulk operations"
4. **Section 9 (Release plan)** — Revised:
   - **v1.0** — Full mock client (unchanged)
   - **v1.1** — Python FastAPI backend + MailPit (local dev) + PostgreSQL
   - **v1.2** — Gmail API integration + KeyCloak auth
   - **v1.3** — Microsoft Graph provider
   - **v2.0** — Calendar + Contacts + Tasks + AI Copilot

5. **New Section 10 — Backend Architecture Summary** — High-level diagram of the config-driven provider system

---

## Implementation Phases

### Phase 1: Foundation (Est. 3-4 days)
- [ ] Project skeleton (`pyproject.toml`, directory structure)
- [ ] Configuration system (Pydantic Settings + YAML)
- [ ] Domain layer (enums, models, errors, requests, responses)
- [ ] Database schema (SQLAlchemy models + Alembic migrations)
- [ ] Docker Compose (Postgres + MailPit)
- [ ] App factory + lifespan + CORS + error handler middleware
- [ ] Auth middleware stub (dev bypass mode)
- [ ] Adapter protocols + registry

### Phase 2: Core Mail Operations (Est. 3-4 days)
- [ ] PostgreSQL storage adapter (repository layer)
- [ ] MailFacade implementation (all message actions)
- [ ] Folder management (system + custom + favorites)
- [ ] Message list with cursor pagination + sorting
- [ ] Thread aggregation
- [ ] API routers: messages, threads, mailbox
- [ ] Demo data seeder (port `webmail_ui/src/data/*`)

### Phase 3: Compose & Send (Est. 2-3 days)
- [ ] ComposeFacade (draft lifecycle)
- [ ] MailPit transport adapter (SMTP send)
- [ ] Send worker (async send queue)
- [ ] Delivery state machine + delivery log
- [ ] API routers: drafts

### Phase 4: Search, Rules & Productivity (Est. 2-3 days)
- [ ] PostgreSQL search adapter (tsvector + trigram)
- [ ] SearchFacade (structured search, suggestions, facets)
- [ ] RulesFacade (CRUD + evaluation engine)
- [ ] Templates, Signatures, Categories, Saved Searches facades
- [ ] Preferences facade
- [ ] API routers: search, rules, templates, signatures, categories, preferences, saved-searches

### Phase 5: Workers & Inbound (Est. 2 days)
- [ ] Snooze wake-up worker
- [ ] Rule evaluation worker
- [ ] MailPit inbound adapter (polling)
- [ ] Sync worker skeleton

### Phase 6: Gmail Provider (Est. 3-4 days)
- [ ] Gmail transport adapter
- [ ] Gmail inbound adapter (API polling + optional push)
- [ ] Gmail sync worker
- [ ] Gmail-specific config YAML
- [ ] Integration tests with Gmail sandbox

### Phase 7: Testing & Polish (Est. 2 days)
- [ ] Unit tests for all facades (>80% coverage)
- [ ] Integration tests for API routes
- [ ] MailPit transport integration test
- [ ] OpenAPI schema validation
- [ ] README with setup instructions

---

## Open Questions

> [!IMPORTANT]
> **1. Database choice for local dev**: PostgreSQL (via Docker) or SQLite for zero-dependency startup? PostgreSQL gives us `tsvector` search and JSONB, but requires Docker. Recommendation: PostgreSQL.

> [!IMPORTANT]
> **2. Gmail OAuth flow**: For Gmail integration, should the backend handle OAuth2 consent flow itself (3-legged OAuth), or assume tokens are provisioned externally (e.g., by KeyCloak as an identity broker)? Recommendation: KeyCloak as identity broker with Gmail as a social connection.

> [!NOTE]
> **3. Multi-tenant**: Should the backend support multiple organizations/tenants from day 1, or single-tenant? The schema supports multi-tenant via `user_id` scoping, but org-level config (like shared rules) is not designed yet.

> [!NOTE]
> **4. WebSocket / SSE**: Should the API support real-time push (new message notifications, draft sync) in Phase 1, or is polling sufficient? Recommendation: Polling in Phase 1, SSE in Phase 2.

---

## Verification Plan

### Automated Tests
```bash
cd runtime/mail_api
# Unit tests
pytest tests/unit/ -v --cov=app --cov-report=term-missing

# Integration tests (requires Docker services)
docker compose up -d postgres mailpit
pytest tests/integration/ -v

# OpenAPI schema check
python -c "from app.main import create_app; import json; print(json.dumps(create_app().openapi(), indent=2))" > openapi.json
```

### Manual Verification
1. **Docker Compose up** → Postgres + MailPit + API all healthy
2. **Seed demo data** → `POST /api/v1/admin/seed` returns 200 with message counts
3. **List messages** → `GET /api/v1/messages?folder_id=inbox` returns seeded messages
4. **Send via MailPit** → Create draft → Send → Verify message appears in MailPit Web UI (port 8025)
5. **Search** → `POST /api/v1/search/messages` with query returns relevant results
6. **Health check** → `GET /api/v1/health` returns status for all adapters
7. **OpenAPI docs** → `http://localhost:8000/docs` shows complete Swagger UI

### Browser Testing
- Start webmail UI (`npm run dev`) and API (`uvicorn`) simultaneously
- Verify API responses match the shape expected by Zustand store types
- Confirm CORS headers allow cross-origin requests from the frontend
