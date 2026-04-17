# PSense Mail — Implementation Plan

**Status**: v1.0 mock client complete. Backend integration not started.
**Last updated**: 2026-04-17

---

## Build status

### ✅ Done

- [x] Brand tokens (oklch palette, sidebar dark purple, rail tokens, status colors)
- [x] PSense logo asset + sidebar header + Powered-by footer badge
- [x] App shell: header, app rail, mail sidebar, layout route (`_app.tsx`, `_app.mail.tsx`)
- [x] Zustand stores: `mail-store`, `compose-store`, `ui-store` (all `persist`-ed)
- [x] Type system: `src/types/mail.ts` (MailMessage, MailFolder, MailRule, MailTemplate, MailSignature, ComposeDraft, UserPreferences)
- [x] Mock data: ~60 messages, threads, attachments, categories, custom folders, rules, templates, signatures
- [x] Mail list with virtualization (`@tanstack/react-virtual`), grouping, multi-select, bulk actions, view tabs
- [x] Reading pane + thread view + recipient/cc expand + trust badge + attachments strip + action toolbar
- [x] All folder routes: inbox, focused, other, drafts, sent, archive, snoozed, flagged, deleted, junk
- [x] Category routes (`/mail/category/$categoryId`) and custom folder routes (`/mail/folder/$folderId`)
- [x] Search route (`_app.mail.search.tsx`) with facets and active filter chips
- [x] Compose window (Tiptap, floating + full-screen + **minimized-to-bar**), draft autosave, scheduled send field
- [x] Compose keyboard shortcuts: `⌘/Ctrl+Enter` send, `⌘/Ctrl+Shift+M` toggle minimize, `Esc` minimize
- [x] Rules center, Templates manager, Mail settings page
- [x] Command palette (⌘K) and keyboard shortcuts modal (`?`) via `global-overlays.tsx`
- [x] Light + dark themes, three density modes, reading pane placement (right/bottom/off)
- [x] Toast notifications with undo for archive/move/delete
- [x] SSR-safe Tiptap config (`immediatelyRender: false`)

### 🚧 Pending / placeholders

- [ ] **Calendar** route — rail icon disabled, no `_app.calendar.*` routes
- [ ] **Contacts** route — rail icon disabled
- [ ] **Tasks** route — rail icon disabled
- [ ] **Settings → Preferences** — currently a redirect card to Mail settings; needs notifications, appearance, shortcuts panels
- [ ] **Signatures editor UI** — data model + store action exist; no management screen
- [ ] **Saved searches UI** — type exists; no save / recall flow
- [ ] **Attachment preview** — file cards render metadata only
- [ ] **Snooze wake-up** — `snoozedUntil` is stored but never fires (needs scheduler)
- [ ] **Scheduled send** — `scheduledFor` stored on draft; no scheduler
- [ ] **Multi-draft stack** — only one compose window at a time (Gmail-style stack not built)
- [ ] **Empty / loading / error skeletons** — partial coverage, audit each surface

### 🔮 Not started (v1.1+)

- [ ] **Lovable Cloud** enabled (DB + Auth + Storage + Edge Functions)
- [ ] **TanStack Query** data layer replacing Zustand mutations
- [ ] **Auth** (sign in / sign up / reset / OAuth)
- [ ] **Real mail provider** (Microsoft Graph / Gmail API / Resend inbound webhook)
- [ ] **AI Copilot** (summarize thread, smart reply, draft assist)
- [ ] **Mobile responsive pass** for narrow viewports
- [ ] **i18n** scaffolding

---

## Build order (forward)

1. **Settings → Preferences** full panel (notifications, appearance, shortcuts toggle)
2. **Signatures management UI** (CRUD, default toggle, insert in compose)
3. **Saved searches** (save + sidebar list + restore)
4. **Multi-draft compose stack** (Gmail-style minimized bar row)
5. **Calendar v0** — month view + event details drawer (mock data)
6. **Contacts v0** — list + detail + group folders (mock data)
7. **Tasks v0** — list + checklist + due date (mock data)
8. **Lovable Cloud enable** + Auth + schema migration
9. **TanStack Query refactor** — wrap each store action in a mutation hook
10. **Real provider integration** — Microsoft Graph first (broadest enterprise coverage)
11. **Edge functions**: snooze wake-up, scheduled send, rule executor, inbound webhook
12. **AI Copilot** via Lovable AI Gateway

---

## Architectural decisions

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| Routing | TanStack Start file-based | Template default; type-safe; SSR-ready |
| State (UI) | Zustand + `persist` | Lightweight, ergonomic, survives refresh |
| State (data, future) | TanStack Query | Standard for server cache; integrates with Start loaders |
| Editor | Tiptap | Best-in-class, extensible, headless |
| Forms | react-hook-form + zod | Where validation matters (rules, settings) |
| Virtualization | `@tanstack/react-virtual` | First-party, handles 10k+ rows |
| Styling | Tailwind v4 + oklch tokens in `src/styles.css` | Per template; semantic tokens only |
| Components | shadcn/ui | Customizable, accessible primitives |
| Backend (target) | Lovable Cloud | Zero-config Postgres + Auth + Storage + Functions |

---

## File map

```
src/
├── routes/
│   ├── __root.tsx                      # shell + providers
│   ├── _app.tsx                        # auth-protected layout (header + rail + footer)
│   ├── _app.mail.tsx                   # mail-specific layout (sidebar + outlet)
│   ├── _app.mail.{inbox,focused,other,drafts,sent,archive,snoozed,flagged,deleted,junk}.tsx
│   ├── _app.mail.folder.$folderId.tsx
│   ├── _app.mail.category.$categoryId.tsx
│   ├── _app.mail.search.tsx
│   ├── _app.rules.tsx
│   ├── _app.templates.tsx
│   ├── _app.settings.mail.tsx
│   ├── _app.settings.preferences.tsx   # 🚧 stub
│   └── index.tsx                       # redirects to /mail/inbox
├── components/
│   ├── layout/{app-header,app-rail,mail-sidebar}.tsx
│   ├── mail/{mail-workspace,message-list,message-row,reading-pane}.tsx
│   ├── compose/compose-window.tsx
│   ├── global-overlays.tsx             # ⌘K palette + ? shortcuts modal
│   ├── powered-by-footer.tsx
│   ├── psense-logo.tsx
│   └── ui/                             # shadcn primitives
├── stores/
│   ├── mail-store.ts                   # messages, folders, rules, templates, signatures
│   ├── compose-store.ts                # open draft + saved drafts
│   └── ui-store.ts                     # density, theme, pane sizes, etc.
├── data/{messages,folders,categories}.ts # mock seed
├── types/mail.ts
├── hooks/use-filtered-messages.ts
├── lib/mail-format.ts
└── styles.css                          # design tokens
```
