# PSense Mail — Business Requirements Document (BRD)

**Product**: PSense Mail
**Owner**: PSense.ai
**Status**: Draft v1.0
**Last updated**: 2026-04-17

---

## 1. Vision

A production-grade enterprise mail workspace that feels as fast and focused as the best modern clients (Superhuman, Hey, Outlook for Business), but **branded for PSense.ai** and designed as the entry point to a broader productivity suite (Calendar, Contacts, Tasks, and beyond).

Mail is the wedge — once a team lives inside PSense Mail, the surrounding surfaces (Calendar, Contacts, Tasks, AI Copilot) become natural extensions of the same workspace.

## 2. Target users

| Persona | Needs |
|---------|-------|
| **Knowledge worker** (sales, CS, ops) | Triaging high-volume inbox, fast keyboard nav, snooze, templates, signatures |
| **Team lead / manager** | Categorization, rules, focused inbox, mentions, OOO |
| **Executive assistant** | Multi-account access (future), scheduled send, delegation (future) |
| **IT admin** (future) | SSO, audit logs, retention policies, DLP, tenant settings |

## 3. Goals & success metrics

| Goal | Metric | Target |
|------|--------|--------|
| Triage speed | Time-to-inbox-zero per session | < 8 min for 50 messages |
| Adoption | DAU / MAU | > 60% within 30 days |
| Compose efficiency | Avg keystrokes per send | -25% vs Outlook web |
| Reliability | Uptime | 99.9% |
| Performance | TTI on inbox | < 1.5s on broadband |

## 4. In scope (v1)

- Three-pane mail UI (rail / sidebar / list+reading pane)
- All standard folders (Inbox, Focused, Other, Drafts, Sent, Archive, Snoozed, Flagged, Deleted, Junk)
- Custom folders + categories + favorites
- Threaded conversations with attachments
- Compose: floating + full-screen + minimized, Tiptap rich text, draft autosave, schedule send
- Search: global autosuggest + dedicated results page with facets
- Productivity: rules, templates, signatures, command palette (⌘K), keyboard shortcuts modal, snooze
- Settings: Mail (reading pane, threading, density, sort, theme, OOO) + Preferences (notifications, appearance)
- Light + dark themes, three density modes
- Accessibility: full keyboard, visible focus rings, ARIA via shadcn primitives

## 5. Out of scope (v1)

- Real mail provider integration (IMAP, Gmail API, Microsoft Graph) — postponed to v2
- Calendar / Contacts / Tasks routes — placeholders only in v1
- Mobile native apps (web responsive only)
- Multi-account, delegation, shared mailboxes
- DLP, retention policies, eDiscovery, compliance exports
- AI Copilot (summarize, draft, smart reply) — v2

## 6. Functional requirements

### 6.1 Mail list
- Grouped by Today / Yesterday / Earlier this week / Older
- Row: avatar, sender, subject, preview, timestamp, badges (flag, pin, attachment, importance, category)
- Multi-select with bulk action toolbar
- View tabs: All / Unread / Focused / Other / Attachments / Mentions
- Keyboard nav: `j/k` move, `x` select, `e` archive, `#` delete, `r` reply, `a` reply-all, `f` forward, `?` shortcuts
- Virtualized for 10k+ rows

### 6.2 Reading pane
- Right / Bottom / Off (user setting)
- Collapsible thread messages
- Recipients with cc/bcc expand, trust badge
- Attachment strip with file cards (preview + download — preview deferred)
- Action toolbar: reply / reply-all / forward / archive / delete / move / categorize / flag / snooze / more

### 6.3 Compose
- Floating window, full-screen, minimized-to-bar modes
- Tiptap editor (bold/italic/underline/lists/quote/code/link/heading)
- Chip-based To/Cc/Bcc with email validation
- Attachments, signatures, templates
- Schedule send + autosave drafts
- Unsaved-changes warning on close
- Shortcuts: `⌘+Enter` send, `⌘+Shift+M` toggle minimize, `Esc` minimize

### 6.4 Search
- Header autosuggest (recent searches, syntax tips: `from:`, `has:attachment`, `is:unread`)
- Results page with facets: sender, date range, has attachment, unread, flagged, category, folder, importance, from-me, mentions
- Active filter chips, save search

### 6.5 Productivity
- Rules center: condition cards (sender/subject/has-attachment/older-than) → action (move/categorize/mark-important/archive/delete)
- Templates manager: name + subject + body
- Signatures: multiple, default toggle
- Command palette (⌘K): folders, settings, compose, theme, search
- Keyboard shortcuts modal (`?`)

### 6.6 Settings
- **Mail**: reading pane placement, threading, focused inbox, density, default sort, preview lines, signatures, OOO, theme, default reply, schedule defaults
- **Preferences**: notifications (desktop, sound, only-focused), appearance, shortcuts on/off

## 7. Non-functional requirements

| Category | Requirement |
|----------|-------------|
| Performance | TTI < 1.5s; list scroll 60fps virtualized |
| Accessibility | WCAG 2.1 AA, full keyboard, visible focus, screen-reader labels |
| Browser support | Latest 2 versions of Chrome, Edge, Safari, Firefox |
| Theming | Light + dark; semantic tokens only; high-contrast in v2 |
| i18n | English v1; structure ready for translation in v2 |
| Security (v2) | RLS per user, signed attachment URLs, MFA, SSO |
| Data residency (v2) | EU + US regions selectable per tenant |

## 8. Risks & open questions

- Real mail provider integration is the largest unknown — Microsoft Graph vs Gmail API vs custom SMTP/IMAP each have very different sync, threading, and webhook semantics.
- Scheduled send and snooze need a real scheduler (edge cron) — currently mock.
- Mobile responsive vs native: revisit after v1 metrics.
- AI Copilot pricing / model choice — pending Lovable AI Gateway decision.

## 9. Release plan

- **v1.0 (current)** — Full mock client, Zustand-only, design system, all surfaces
- **v1.1** — Lovable Cloud backend (auth, DB, storage), TanStack Query data layer
- **v1.2** — Real mail provider integration (Microsoft Graph first)
- **v2.0** — Calendar + Contacts + Tasks + AI Copilot
