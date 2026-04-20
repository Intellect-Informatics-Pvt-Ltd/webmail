# PSense Mail

A production-grade, enterprise webmail workspace built for **PSense.ai** — designed to compete with modern clients like Superhuman and Hey, while providing the control and extensibility that enterprise IT teams demand.

---

## 1. Problem Statement

Enterprise teams struggle with fragmented mail experiences:

- **Legacy webmail** (Roundcube, OWA) is slow, cluttered, and feature-poor.
- **Consumer clients** (Gmail, Apple Mail) lack multi-tenancy, audit trails, SSO, and compliance controls.
- **Modern productivity clients** (Superhuman, Hey) are SaaS-only with no self-hosted option and limited provider support.

PSense Mail closes this gap by delivering a fast, keyboard-driven, offline-capable mail workspace that:

- Integrates with **any POP3/SMTP/Gmail/Microsoft Graph** mail provider.
- Runs self-hosted behind your own infrastructure (no vendor lock-in).
- Supports **multi-tenancy** and **multi-account** from day one.
- Is designed for extension into Calendar, Contacts, Tasks, and AI Copilot — sharing a unified shell and data layer.

---

## 2. Architecture

```
┌──────────────────────────────┐         ┌──────────────────────────────────┐
│   Browser (React 19 Client)  │         │   FastAPI Backend (Python 3.12)  │
│                              │         │                                  │
│  TanStack Query cache ───────┼─HTTPS──▶│  Routers  ──▶  Façade Services  │
│         │                    │         │     │               │            │
│         ▼                    │         │     │               ▼            │
│  Dexie (IndexedDB)           │         │     │          Adapters          │
│  ├─ entity cache             │         │     │          ├─ transport      │
│  ├─ outbox (sends)           │         │     │          ├─ inbound (POP3) │
│  ├─ op-log (actions)         │         │     │          ├─ file storage   │
│  └─ attachment blobs         │         │     │          └─ search         │
│                              │         │     ▼               ▼            │
│  Service Worker (PWA)        │         │   MongoDB        File stores     │
│  ├─ shell precache           │         │   (Beanie ODM)   (NAS/S3/...)   │
│  ├─ runtime cache            │         │                                  │
│  └─ background sync          │         │  Workers (in-process)            │
│                              │         │  ├─ inbound poller               │
│  Zustand (ephemeral UI)      │         │  ├─ snooze wake-up              │
│                              │         │  ├─ scheduled send               │
└──────────────────────────────┘         │  └─ retry / DLQ                  │
                                         └──────────────┬───────────────────┘
                                                        │
                                                        ▼
                                              External Services:
                                              • MongoDB (separate)
                                              • KeyCloak (OIDC/SSO)
                                              • Mailpit (dev only)
                                              • Gmail / SMTP / POP3
                                              • Redis (Phase 5 — ARQ queue)
```

### Key Design Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | Offline-aware from day one | Every read goes through IDB cache; every write goes through a queue that tolerates disconnection |
| 2 | Tenant + account scoping everywhere | Every row carries `tenant_id` and `account_id` — retrofitting this later is 10x harder |
| 3 | Idempotency on every mutation | All writes accept `Idempotency-Key` + `If-Match` (expected version) — replay-safe by default |
| 4 | Adapters over branching | Provider-specific logic lives behind protocols; services never reference concrete adapters |
| 5 | TypeScript and Python share a contract | OpenAPI spec is the single source of truth; client regenerates types from it |
| 6 | Semantic tokens only | No hardcoded colors — everything goes through CSS design tokens |

---

## 3. Code Structure

```
webmail/
├── runtime/mail_api/          # Python FastAPI backend
│   ├── app/
│   │   ├── adapters/          # Pluggable provider implementations
│   │   │   ├── db/            #   MongoDB / Memory database adapters
│   │   │   ├── inbound/       #   POP3, Gmail, Mailpit, Memory inbound
│   │   │   ├── transport/     #   SMTP, Gmail, Mailpit outbound
│   │   │   ├── file_storage/  #   NAS, S3, Azure Blob, GCS
│   │   │   ├── search/        #   MongoDB text index, Meilisearch (scaffold)
│   │   │   ├── protocols.py   #   Protocol base classes (interfaces)
│   │   │   └── registry.py    #   Configuration-driven adapter factory
│   │   ├── api/routers/       # HTTP endpoint definitions (15 routers)
│   │   ├── domain/            # Beanie document models, enums, errors
│   │   ├── middleware/        # Auth, CORS, correlation ID, error handling
│   │   ├── services/          # Business logic façades (11 services)
│   │   ├── workers/           # Background tasks (poller, scheduler, retry)
│   │   ├── seed/              # Demo data seeder for development
│   │   └── main.py            # Application factory + lifespan
│   ├── config/
│   │   ├── default.yaml       # Base configuration defaults
│   │   └── settings.py        # Pydantic Settings with YAML + env merge
│   ├── tests/                 # pytest test suite
│   ├── docker-compose.yaml    # Base compose (API only)
│   ├── docker-compose.dev.yaml    # Dev overlay (adds Mailpit)
│   ├── docker-compose.prod.yaml   # Prod overlay (real SMTP/POP3)
│   ├── Dockerfile             # Python 3.12-slim container
│   └── pyproject.toml         # Dependencies + build config
│
├── webmail_ui/                # React 19 frontend
│   ├── src/
│   │   ├── routes/            # TanStack Start file-based routing
│   │   ├── components/
│   │   │   ├── layout/        # AppHeader, AppRail, MailSidebar
│   │   │   ├── mail/          # MailWorkspace, MessageList, ReadingPane
│   │   │   ├── compose/       # ComposeWindow (Tiptap editor)
│   │   │   ├── calendar/      # Calendar views (placeholder)
│   │   │   ├── contacts/      # Contacts views (placeholder)
│   │   │   └── ui/            # shadcn/ui primitives (46 components)
│   │   ├── stores/            # Zustand state (mail, compose, UI)
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # Utilities, API client, PWA registration
│   │   ├── types/             # TypeScript domain types
│   │   └── styles.css         # Design tokens (oklch, single source of truth)
│   ├── package.json
│   └── vite.config.ts
│
└── thoughts/shared/plans/     # Product specs and roadmap
    └── 05-roadmap.md          # Single source of truth for requirements
```

---

## 4. Where to Look for What

| You want to... | Look here |
|----------------|-----------|
| Understand the full product roadmap | `thoughts/shared/plans/05-roadmap.md` |
| Add a new API endpoint | `runtime/mail_api/app/api/routers/` — create router, register in `main.py` |
| Add business logic | `runtime/mail_api/app/services/` — add/modify a façade |
| Add a new provider adapter | `runtime/mail_api/app/adapters/` — implement protocol, wire in `registry.py` |
| Add a new database model | `runtime/mail_api/app/domain/models.py` — add Beanie Document |
| Change configuration | `runtime/mail_api/config/settings.py` + `config/default.yaml` |
| Add a new frontend route | `webmail_ui/src/routes/` — TanStack Start file-based (auto-registers) |
| Modify the sidebar/header | `webmail_ui/src/components/layout/` |
| Add a new UI component | `webmail_ui/src/components/ui/` — use shadcn/ui CLI |
| Change colors/theme | `webmail_ui/src/styles.css` — CSS tokens in `:root` / `.dark` |
| Manage frontend state | `webmail_ui/src/stores/` — Zustand stores |
| Run backend tests | `cd runtime/mail_api && pytest` |
| Run frontend tests | `cd webmail_ui && npm run test:run` |
| Generate API types | `cd webmail_ui && npm run gen:api` (backend must be running) |

---

## 5. Features

### Shipped (v1.0)

**Frontend:**
- Three-pane mail UI (rail + sidebar + list/reading pane)
- All system folders: Inbox, Focused, Other, Sent, Drafts, Archive, Snoozed, Flagged, Deleted, Junk
- Custom folders and categories with color coding
- Threaded conversations with attachments strip
- Compose window: floating, full-screen, minimized modes with Tiptap rich-text editor
- Multi-select, bulk actions, keyboard shortcuts, command palette (`⌘K`)
- Rules center, templates manager, signatures management
- Light/dark themes, three density modes, reading pane placement
- Toast notifications with undo
- Accounts & sync settings page (POP3 configuration UI)
- Sync status indicator in sidebar

**Backend:**
- FastAPI async application with 15 API routers
- Full CRUD for messages, threads, drafts, folders, categories, rules, templates, signatures, preferences, saved searches
- Pluggable adapter architecture (transport, inbound, file storage, search, database)
- POP3 inbound adapter with MIME parsing, deduplication (seen-ID store), and acknowledge/delete
- Mailpit transport adapter with SMTP retry logic
- Background workers: inbound poller, snooze scheduler, retry handler
- Multi-tenant/multi-account data model with soft deletes
- Idempotency records and op-log for delta sync
- KeyCloak OIDC auth (configurable, disabled in dev)
- File storage: NAS (local), S3, Azure Blob, GCS adapters

### Planned (v1.1+)

- TanStack Query wiring (replace mocked data with live API)
- Offline support via IndexedDB (Dexie) + service worker
- HTML sanitization (DOMPurify + sandboxed iframe)
- Microsoft Graph provider integration
- OpenTelemetry observability + Prometheus metrics
- ARQ (Redis) worker queue for horizontal scaling
- GDPR export/delete endpoints
- Calendar, Contacts, Tasks modules

---

## 6. Docker Structure & Deployment

### File Layout

| File | Purpose |
|------|---------|
| `docker-compose.yaml` | **Base** — defines the API service only (MongoDB is external) |
| `docker-compose.dev.yaml` | **Dev overlay** — adds Mailpit sandbox for local mail testing |
| `docker-compose.prod.yaml` | **Prod overlay** — configures real SMTP/POP3 providers via env vars |
| `Dockerfile` | Python 3.12-slim, installs from `pyproject.toml`, runs uvicorn on port 8000 |

### Development

```bash
# Prerequisites: MongoDB running separately (localhost:27017)

cd runtime/mail_api

# Start API + Mailpit
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up

# Services available:
#   API:           http://localhost:8000
#   Mailpit UI:    http://localhost:8025
#   Mailpit SMTP:  localhost:1025
#   Mailpit POP3:  localhost:1110
```

**Enabling real email delivery in dev** (via Mailpit SMTP relay):

Uncomment the relay section in `docker-compose.dev.yaml`:
```yaml
MP_SMTP_RELAY_HOST: "smtp.gmail.com"
MP_SMTP_RELAY_PORT: "587"
MP_SMTP_RELAY_STARTTLS: "true"
MP_SMTP_RELAY_AUTH: "login"
MP_SMTP_RELAY_USERNAME: "your-gmail@gmail.com"
MP_SMTP_RELAY_PASSWORD: "your-app-password"  # Gmail App Password
MP_SMTP_RELAY_ALL: "true"
```

### Production

```bash
cd runtime/mail_api

# All credentials via environment variables (or .env file)
SMTP_HOST=smtp.gmail.com \
SMTP_USERNAME=you@domain.com \
SMTP_PASSWORD=app-password \
SMTP_FROM_ADDRESS=noreply@domain.com \
POP3_HOST=pop.gmail.com \
POP3_USERNAME=you@domain.com \
POP3_PASSWORD=app-password \
MONGO_URI=mongodb://prod-mongo:27017 \
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
```

The prod overlay uses `${VAR:?Set VAR}` syntax — Docker will fail fast with a clear error if any required credential is missing.

### Environment Variables

All backend configuration can be overridden via env vars with the prefix `PSENSE_MAIL__` and double-underscore nesting:

```
PSENSE_MAIL__DATABASE__BACKEND=mongo
PSENSE_MAIL__DATABASE__MONGO__URI=mongodb://...
PSENSE_MAIL__PROVIDER__ACTIVE=pop3
PSENSE_MAIL__PROVIDER__POP3__HOST=pop.gmail.com
PSENSE_MAIL__PROVIDER__POP3__PORT=995
PSENSE_MAIL__PROVIDER__POP3__TLS_MODE=ssl
PSENSE_MAIL__AUTH__ENABLED=true
PSENSE_MAIL__AUTH__ISSUER=https://keycloak.domain.com/realms/psense
PSENSE_MAIL__FILE_STORAGE__BACKEND=s3
PSENSE_MAIL__FILE_STORAGE__S3__BUCKET=psense-mail-attachments
```

---

## 7. Development Guide

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 20+ | Frontend build |
| MongoDB | 7.x | Database (installed separately) |
| Docker | 24+ | Containerized deployment |

### Backend Setup

```bash
cd runtime/mail_api

# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies (with dev extras)
pip install -e ".[dev]"

# Run locally (no Docker)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
pytest

# Lint
ruff check .
```

### Frontend Setup

```bash
cd webmail_ui

# Install dependencies
npm install

# Development server (hot reload)
npm run dev

# Build for production
npm run build

# Lint + format
npm run lint
npm run format

# Run tests
npm run test:run

# Generate API types from running backend
npm run gen:api
```

### Configuration Priority (highest → lowest)

1. **Environment variables** (`PSENSE_MAIL__*`)
2. **Environment-specific YAML** (`config/{PSENSE_MAIL_ENV}.yaml`)
3. **Default YAML** (`config/default.yaml`)
4. **Pydantic model defaults**

---

## 8. Tech Stack Summary

### Backend

| Component | Technology |
|-----------|------------|
| Framework | FastAPI 0.115+ (async) |
| Runtime | uvicorn + Python 3.12 |
| Database | MongoDB 7 + Beanie ODM |
| Config | Pydantic Settings + YAML |
| Auth | KeyCloak OIDC (python-jose JWT) |
| Mail Transport | aiosmtplib (SMTP) |
| Mail Inbound | poplib (POP3) via asyncio executor |
| File Storage | aiofiles (NAS), aiobotocore (S3), Azure SDK, GCS SDK |
| Logging | structlog (JSON) |
| IDs | python-ulid (sortable, unique) |
| Testing | pytest + pytest-asyncio |
| Linting | ruff |

### Frontend

| Component | Technology |
|-----------|------------|
| Framework | TanStack Start v1 (SSR-capable) |
| UI Library | React 19 + TypeScript 5.8 |
| Styling | Tailwind CSS v4 + oklch design tokens |
| Components | shadcn/ui (Radix primitives) |
| State (server) | TanStack Query v5 |
| State (UI) | Zustand v5 |
| Persistence | Dexie v4 (IndexedDB) |
| Editor | Tiptap v3 |
| Virtualization | @tanstack/react-virtual |
| PWA | Workbox v7 |
| Forms | react-hook-form + zod |
| Build | Vite 7 |
| Testing | Vitest |

---

## 9. API Endpoint Overview

All endpoints are served under `/api/v1/` (when versioned prefix is enabled):

| Router | Endpoints | Purpose |
|--------|-----------|---------|
| `accounts` | GET/PATCH pop3, POST test/sync, GET status | POP3 configuration and sync control |
| `messages` | CRUD + actions (read, flag, archive, move) | Message retrieval and state management |
| `threads` | GET list, GET detail | Conversation threading |
| `drafts` | CRUD + send | Draft composition with auto-save |
| `attachments` | Upload, download, delete | File handling with chunked upload |
| `mailbox` | CRUD folders | Folder management |
| `categories` | CRUD | Custom category management |
| `rules` | CRUD + execute | Email filtering rules |
| `templates` | CRUD | Canned response templates |
| `signatures` | CRUD | Email signatures |
| `preferences` | GET/PATCH | User UI/notification preferences |
| `saved_searches` | CRUD | Persisted search queries |
| `search` | GET | Full-text search across messages |
| `sync` | GET delta | Op-log streaming for offline sync |
| `admin` | Tenant/user management | Administrative operations |

---

## 10. Testing

### Backend

```bash
cd runtime/mail_api
pytest                       # Run all tests
pytest -v                    # Verbose output
pytest tests/test_pop3_adapter.py  # Run specific test file
pytest --cov=app             # With coverage
```

Current test coverage: POP3 adapter (34 tests), API basics, façade unit tests.

### Frontend

```bash
cd webmail_ui
npm run test:run             # Single run
npm run test                 # Watch mode
npm run test:coverage        # With coverage
```

---

## 11. Deployment Checklist

For production deployments, ensure:

- [ ] MongoDB is running and accessible from the API container
- [ ] All required env vars are set (SMTP, POP3, MongoDB URI)
- [ ] `PSENSE_MAIL__AUTH__ENABLED=true` with valid KeyCloak config
- [ ] File storage backend configured (S3/Azure/GCS for cloud, NAS for on-prem)
- [ ] TLS termination in front of the API (nginx/Traefik/cloud LB)
- [ ] `PSENSE_MAIL__APP__CORS_ORIGINS` set to your frontend domain
- [ ] `PSENSE_MAIL__LOGGING__LEVEL=INFO` (not DEBUG in prod)
- [ ] Volume mount for attachments if using NAS backend
- [ ] Health check endpoint available at `/health`
- [ ] Monitoring/alerting on worker failures (inbound poller, retry queue)

---

## 12. Contributing

1. All source code changes go through PR review.
2. Backend: run `ruff check .` and `pytest` before pushing.
3. Frontend: run `npm run lint` and `npm run test:run` before pushing.
4. Update `thoughts/shared/plans/05-roadmap.md` when shipping a phase milestone.
5. Follow existing patterns — check `runtime/mail_api/app/adapters/` for adapter examples, `app/api/routers/` for endpoint patterns.

---

## License

Proprietary — PSense.ai. All rights reserved.
