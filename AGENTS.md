# AGENTS.md — PSense Mail

This file is the Kiro/agent binding layer for **PSense Mail**. It points to the platform-neutral toolkit in `.project/` and provides project-specific context. Keep this file slim — all reusable logic lives in `.project/`.

---

## Project overview

**PSense Mail** is a production-grade enterprise mail workspace built on:

- **TanStack Start v1** (file-based routing, SSR-ready)
- **React 19 + Vite 7**
- **Tailwind v4** with `oklch` design tokens in `webmail_ui/src/styles.css`
- **shadcn/ui** (Radix primitives, never roll custom focus traps or ARIA)
- **Zustand v5** with `persist` for client state
- **Tiptap v3** for the compose editor
- **`@tanstack/react-virtual`** for virtualized message lists

All source code lives under `webmail_ui/`. Plans, specs, and research live under `thoughts/`.

---

## Toolkit binding

| Resource | Location |
|----------|----------|
| Agent playbooks | `.project/agents/` |
| Command playbooks | `.project/commands/` |
| Project plans & BRD | `thoughts/shared/plans/` |
| Design system spec | `thoughts/shared/plans/03-design-system.md` |
| Backend architecture | `thoughts/shared/plans/04-backend-architecture.md` |
| Python backend spec | `thoughts/shared/plans/mail_backend_facade_spec.md` |

### Quick-start for any agent

1. Read `thoughts/shared/plans/00-README.md` for the project index.
2. Pick a role playbook from `.project/agents/`.
3. Pick a workflow command from `.project/commands/`.
4. For codebase specifics, start in `webmail_ui/src/`.

---

## Available agent roles

| Agent | When to use |
|-------|-------------|
| `codebase-analyzer` | Understand HOW specific code works (data flow, logic, patterns) |
| `codebase-locator` | Find WHERE files and components live |
| `codebase-pattern-finder` | Find existing patterns to model new work after |
| `thoughts-analyzer` | Deep-dive on a research or planning document |
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
│   │   ├── __root.tsx           # Shell + providers
│   │   ├── _app.tsx             # Auth-protected layout (header + rail + footer)
│   │   ├── _app.mail.tsx        # Mail layout (sidebar + outlet)
│   │   ├── _app.mail.{inbox,focused,other,drafts,sent,archive,snoozed,flagged,deleted,junk}.tsx
│   │   ├── _app.mail.folder.$folderId.tsx
│   │   ├── _app.mail.category.$categoryId.tsx
│   │   ├── _app.mail.search.tsx
│   │   ├── _app.rules.tsx
│   │   ├── _app.templates.tsx
│   │   ├── _app.settings.mail.tsx
│   │   └── _app.settings.preferences.tsx  # 🚧 stub
│   ├── components/
│   │   ├── layout/              # AppHeader, AppRail, MailSidebar
│   │   ├── mail/                # MailWorkspace, MessageList, MessageRow, ReadingPane
│   │   ├── compose/             # ComposeWindow (Tiptap)
│   │   ├── calendar/            # 🚧 placeholder components
│   │   ├── contacts/            # 🚧 placeholder components
│   │   ├── global-overlays.tsx  # ⌘K palette + ? shortcuts modal
│   │   ├── powered-by-footer.tsx
│   │   ├── psense-logo.tsx
│   │   ├── theme-manager.tsx
│   │   └── ui/                  # shadcn primitives (never modify directly)
│   ├── stores/
│   │   ├── mail-store.ts        # messages, folders, rules, templates, signatures
│   │   ├── compose-store.ts     # open draft + saved drafts
│   │   └── ui-store.ts          # density, theme, pane sizes, prefs
│   ├── data/                    # Mock seed data (messages, folders, categories)
│   ├── types/mail.ts            # All domain types
│   ├── hooks/                   # use-filtered-messages, use-mobile
│   ├── lib/                     # mail-format, calendar-utils
│   └── styles.css               # Design tokens (single source of truth for all colors)
└── package.json
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

### State
- **Zustand** for all client state today (v1.0 is 100% client-side, no network).
- Stores are persisted: `psense-mail-data`, `psense-compose`, per-key UI prefs.
- Future (v1.1+): Zustand stays for ephemeral UI only; server data moves to **TanStack Query**.

### Routing
- File-based TanStack Start routes under `src/routes/`.
- Protected routes live under the `_app` layout.
- Mail routes live under `_app.mail`.

### Testing
- No test framework is set up yet (v1.0 is a mock client).
- When adding tests, use **Vitest** (standard for Vite projects) with `--run` flag for single execution.

---

## Build & dev commands

```bash
# All commands run from webmail_ui/
cd webmail_ui

npm run dev        # Start dev server (run manually — do not use as a background process)
npm run build      # Production build
npm run lint       # ESLint
npm run format     # Prettier
```

---

## Current build status

### ✅ Complete (v1.0 mock client)
- Full three-pane mail UI with all standard folders
- Compose window (Tiptap, floating / full-screen / minimized)
- Search with facets, rules center, templates manager
- Command palette (⌘K), keyboard shortcuts modal (?), toast notifications
- Light/dark themes, three density modes, reading pane placement

### 🚧 Pending (next up)
- Settings → Preferences full panel
- Signatures management UI
- Saved searches UI
- Multi-draft compose stack
- Calendar v0, Contacts v0, Tasks v0

### 🔮 Not started (v1.1+)
- Lovable Cloud backend (Postgres + Auth + Storage + Edge Functions)
- TanStack Query data layer
- Real mail provider integration (Microsoft Graph first)
- AI Copilot

---

## Thoughts directory

```
thoughts/
└── shared/
    └── plans/
        ├── 00-README.md              # Project index
        ├── 01-brd.md                 # Business requirements
        ├── 02-implementation-plan.md # Build status + build order
        ├── 03-design-system.md       # Brand tokens, typography, components
        ├── 04-backend-architecture.md # Target Cloud schema, RLS, edge functions
        └── mail_backend_facade_spec.md # Python FastAPI backend contract
```

---

## Python backend (future)

A Python FastAPI backend is specced in `thoughts/shared/plans/mail_backend_facade_spec.md`. It is **not yet implemented**. Key design points:

- Async-first, provider-agnostic, typed
- Façades: `MailFacade`, `ComposeFacade`, `SearchFacade`, `AttachmentFacade`, `AdminFacade`
- Domain exceptions hierarchy rooted at `MailDomainError`
- Local dev mode targets MailPit as the transport sink
- Source layout: `app/{api,domain,services,adapters,workers}/`

---

## References

- Platform-neutral toolkit: `.project/README.md`
- Agent template: `.project/agents/TEMPLATE.md`
- Command template: `.project/commands/TEMPLATE.md`
