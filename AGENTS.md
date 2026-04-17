# AGENTS.md — PSense Mail

This file is the agent binding layer for **PSense Mail**. It points to the platform-neutral toolkit in `.project/` and provides project-specific context. Keep this file slim — all reusable logic lives in `.project/`.

---

## Project overview

**PSense Mail** is a production-grade enterprise mail workspace built on:

- **TanStack Start v1** (file-based routing, SSR-ready)
- **React 19 + Vite 7**
- **Tailwind v4** with `oklch` design tokens in `webmail_ui/src/styles.css`
- **shadcn/ui** (Radix primitives, never roll custom focus traps or ARIA)
- **Zustand v5** (ephemeral UI-only state — selection, overlays, pane sizes)
- **TanStack Query v5** (server cache, IDB-persisted)
- **Dexie** (IndexedDB — entity cache, outbox, op-log, blobs)
- **Tiptap v3** for the compose editor
- **`@tanstack/react-virtual`** for virtualized message lists

Frontend source lives under `webmail_ui/`.
Backend source lives under `runtime/mail_api/` (FastAPI + MongoDB via Beanie).
Plans, specs, and research live under `thoughts/`.

---

## Toolkit binding

| Resource | Location |
|----------|----------|
| Agent playbooks | `.project/agents/` |
| Command playbooks | `.project/commands/` |
| **Unified roadmap (single source of truth)** | `thoughts/shared/plans/05-roadmap.md` |

### Quick-start for any agent

1. Read `thoughts/shared/plans/05-roadmap.md` for full product context, architecture, data model, API contract, offline design, and phased plan.
2. Pick a role playbook from `.project/agents/`.
3. Pick a workflow command from `.project/commands/`.
4. For frontend specifics, start in `webmail_ui/src/`.
5. For backend specifics, start in `runtime/mail_api/app/`.

---

## Available agent roles

| Agent | When to use |
|-------|-------------|
| `codebase-analyzer` | Understand HOW specific code works (data flow, logic, patterns) |
| `codebase-locator` | Find WHERE files and components live |
| `codebase-pattern-finder` | Find existing patterns to model new work after |
| `thoughts-analyzer` | Deep-dive on the roadmap or a planning document |
| `thoughts-locator` | Discover relevant docs in `thoughts/` |
| `web-search-researcher` | Find current external docs, library versions, best practices |

---

## Available commands

| Command | When to use |
|---------|-------------|
| `create_plan` | Turn a ticket or idea into a phased implementation plan |
| `implement_plan` | Execute an approved plan from `thoughts/shared/plans/` |
| `validate_plan` | Verify a plan was correctly implemented |
| `research_codebase` | Answer a broad question by exploring the codebase |
| `debug` | Investigate a runtime issue via logs, DB state, and git |
| `commit` | Create clean, atomic git commits for session changes |
| `describe_pr` | Generate a comprehensive PR description |
| `founder_mode` | Retroactively organize experimental work into branches + tickets |
| `linear` | Create or update Linear tickets from thoughts documents |
| `local_review` | Set up a worktree for reviewing a colleague's branch |

---

## Codebase map

```
webmail_ui/
├── src/
│   ├── routes/                  # TanStack Start file-based routes
│   │   ├── __root.tsx           # Shell + providers (QueryClientProvider, ShortcutProvider)
│   │   ├── _app.tsx             # Auth-protected layout (header + rail + footer)
│   │   ├── _app.mail.tsx        # Mail layout (sidebar + outlet)
│   │   ├── _app.mail.{inbox,focused,other,drafts,sent,archive,snoozed,flagged,deleted,junk}.tsx
│   │   ├── _app.mail.folder.$folderId.tsx
│   │   ├── _app.mail.category.$categoryId.tsx
│   │   ├── _app.mail.search.tsx
│   │   ├── _app.rules.tsx
│   │   ├── _app.templates.tsx
│   │   ├── _app.settings.mail.tsx
│   │   ├── _app.settings.preferences.tsx
│   │   ├── _app.settings.signatures.tsx
│   │   ├── _app.calendar.tsx / .day / .week / .month
│   │   └── _app.contacts.tsx / .index / .$contactId
│   ├── components/
│   │   ├── layout/              # AppHeader, AppRail, MailSidebar
│   │   ├── mail/                # MailWorkspace, MessageList, MessageRow, ReadingPane
│   │   ├── compose/             # ComposeWindow (Tiptap)
│   │   ├── calendar/            # CalendarView components
│   │   ├── contacts/            # ContactList, ContactDetail
│   │   ├── global-overlays.tsx  # ⌘K palette + ? shortcuts modal
│   │   ├── powered-by-footer.tsx
│   │   ├── psense-logo.tsx
│   │   ├── theme-manager.tsx
│   │   └── ui/                  # shadcn primitives (never modify directly)
│   ├── stores/
│   │   ├── mail-store.ts        # ⚠ TRANSITIONAL — being migrated to TanStack Query
│   │   ├── compose-store.ts     # open draft reference (drafts live in Dexie after Phase 2)
│   │   └── ui-store.ts          # density, theme, pane sizes, prefs (ephemeral UI only)
│   ├── lib/
│   │   ├── db/                  # Dexie schema + singleton (IDB storage)
│   │   ├── api/                 # Generated OpenAPI types + hand-rolled fetch client
│   │   ├── query/               # QueryClient factory, IDB persister, key factories
│   │   ├── shortcuts/           # Central shortcut registry + provider + hook
│   │   ├── sync/                # Delta replay, outbox drain, op-log drain
│   │   ├── mail-format.ts
│   │   ├── calendar-utils.ts
│   │   └── utils.ts
│   ├── hooks/
│   │   ├── queries/             # useMessages, useThread, useFolders, usePreferences, …
│   │   ├── mutations/           # useToggleRead, useArchive, useSendDraft, …
│   │   └── ui/                  # use-mobile, use-shortcut
│   ├── data/                    # Mock seed data (still used by Zustand fallback path)
│   ├── types/mail.ts            # All domain types
│   └── styles.css               # Design tokens (single source of truth for all colors)
└── package.json

runtime/mail_api/
├── app/
│   ├── api/routers/             # All FastAPI routers (prefix /api/v1)
│   ├── domain/                  # enums, errors, models (Beanie), requests, responses
│   ├── services/                # Façades: mail, compose, search, attachment, admin, …
│   ├── adapters/                # db (mongo), transport, file_storage, search, inbound
│   ├── middleware/              # auth, correlation, error_handler, idempotency
│   ├── workers/                 # scheduler, snooze, retry, inbound_poller
│   ├── seed/                    # demo_data.py
│   └── main.py                  # App factory + lifespan
├── config/
│   ├── default.yaml             # Default config (auth: KeyCloak, db: mongo/memory)
│   └── settings.py
└── tests/                       # pytest + pytest-asyncio + mongomock
```

---

## Key conventions

### Styling
- **All colors via CSS tokens** — never `bg-purple-600` or hardcoded hex. Use `bg-primary`, `bg-sidebar`, etc.
- Tokens are defined in `webmail_ui/src/styles.css` (`:root` for light, `.dark` for dark).
- When adding a new semantic color, update `@theme inline`, `:root`, and `.dark` in one edit.

### Components
- Use **shadcn/ui primitives** from `src/components/ui/` — never roll custom focus traps or ARIA.
- Icons: **lucide-react only** (16px dense, 20px elsewhere).
- Motion: **framer-motion only** for compose open/close, command palette, toast. No bouncy springs.
- Every list surface needs an **empty state** (icon + headline + optional CTA).

### State architecture (Phase 1+ shape)
- **TanStack Query** for all server data (messages, threads, folders, drafts, templates, rules, …).
- **Dexie (IDB)** as the Query persister + outbox + op-log + attachment blobs. Never `localStorage` for mail data.
- **Zustand** for ephemeral UI only (selection, overlay open/close, pane sizes, reading-pane placement, theme).
- **`mail-store.ts`** is transitional — being deleted after Phase 2 API cutover. Do not add new data to it.

### API client
- All fetch calls go through `src/lib/api/client.ts` (injects auth header, `X-Correlation-ID`, `Idempotency-Key`, decodes error envelope).
- Types are generated from the backend's `/openapi.json` via `npm run gen:api`.
- Never import `types.gen.ts` directly from components — always go through a typed hook.

### Keyboard shortcuts
- All shortcuts are registered in `src/lib/shortcuts/registry.ts` via `registerShortcut()`.
- The `?` modal reads from the registry — it is the canonical list.
- Use `useShortcut(id)` hook in components — do NOT add raw `keydown` listeners.

### Routing
- File-based TanStack Start routes under `src/routes/`.
- Protected routes live under the `_app` layout.
- Mail routes live under `_app.mail`.

### Testing
- **Frontend**: Vitest + `@testing-library/react`. Run with `npm run test` in `webmail_ui/`.
- **Backend**: pytest + pytest-asyncio + mongomock. Run with `pytest` in `runtime/mail_api/`.
- Unit tests live alongside the source; integration tests in `tests/` at the respective root.

---

## Build & dev commands

```bash
# Frontend — run from webmail_ui/
npm run dev          # Start dev server
npm run build        # Production build
npm run test         # Vitest unit tests
npm run test:run     # Single-run tests (CI)
npm run lint         # ESLint
npm run format       # Prettier
npm run gen:api      # Regenerate OpenAPI TypeScript types from backend

# Backend — run from runtime/mail_api/
uvicorn app.main:app --reload --port 8000   # Dev server
pytest                                       # All tests
pytest tests/test_api_basic.py -v           # Specific test file
```

---

## Current build status

### ✅ Complete (v1.0 mock client + Phase 0)
- Full three-pane mail UI with all standard folders
- Calendar (day/week/month) and Contacts routes
- Signatures settings UI
- Compose window (Tiptap, floating / full-screen / minimized)
- Search with facets, rules center, templates manager
- Command palette (⌘K), keyboard shortcuts modal (?), toast notifications
- Light/dark themes, three density modes, reading pane placement
- FastAPI backend scaffolded with all façades, adapters, workers (in-process)
- Documentation consolidated into `thoughts/shared/plans/05-roadmap.md`

### 🚧 In progress (Phase 1)
- Dexie IDB storage layer replacing localStorage for mail data
- Typed OpenAPI SDK (openapi-typescript)
- TanStack Query mounted with IDB persister
- Central keyboard shortcut registry
- Backend: tenant_id / account_id on all models
- Backend: idempotency middleware
- Backend: op-log collection + delta sync endpoint

### 🔮 Not started (Phase 2+)
- Full API cutover (TanStack Query hooks for all surfaces)
- Compose outbox (offline send queue)
- Service worker (Workbox, offline shell)
- Delta sync client (Tier 4 offline)
- Safe HTML rendering (DOMPurify + sandboxed iframe) — Phase 4
- KeyCloak SSO enabled — Phase 4
- ARQ external worker queue — Phase 5
- Microsoft Graph provider — Phase 6

---

## Thoughts directory

```
thoughts/
└── shared/
    └── plans/
        ├── 00-README.md              # Index (points here)
        └── 05-roadmap.md             # ← THE document; all plans live here
```

---

## Backend (Python FastAPI)

Located at `runtime/mail_api/`. Key design points from `thoughts/shared/plans/05-roadmap.md §18`:

- Async-first, provider-agnostic, typed.
- Façades: `MailFacade`, `ComposeFacade`, `SearchFacade`, `AttachmentFacade`, `AdminFacade`, plus CRUD facades for rules, templates, signatures, categories, preferences, saved searches.
- Domain exceptions hierarchy rooted at `MailDomainError` (`app/domain/errors.py`).
- Adapter registry pattern: `AdapterRegistry` selects concrete adapters from config (transport, storage, search).
- Local dev mode: `database.backend=memory`, `provider.active=memory`, `auth.enabled=false`.
- Auth target: KeyCloak OIDC (configured in `config/default.yaml`, disabled by default for dev).
- Workers: currently in-process via `WorkerManager`; Phase 5 moves to ARQ + Redis.

---

## References

- Platform-neutral toolkit: `.project/README.md`
- Agent template: `.project/agents/TEMPLATE.md`
- Command template: `.project/commands/TEMPLATE.md`
- Unified roadmap: `thoughts/shared/plans/05-roadmap.md`
