# PSense Mail — Backend & Data Architecture

**Status**: Target design — not yet implemented. v1.0 is 100% client-side (Zustand + localStorage).
**Last updated**: 2026-04-17

---

## 1. Current state (v1.0)

Everything lives in the browser:

| Store | Persisted key | Contents |
|-------|---------------|----------|
| `useMailStore` | `psense-mail-data` | messages, folders, customFolders, favorites, rules, templates, signatures |
| `useComposeStore` | `psense-compose` | open draft + saved drafts |
| `useUIStore` | (per-key) | density, theme, reading pane, sidebar widths, prefs |

**Mutations are synchronous Zustand actions.** No fetch, no network, no auth. Mock data is seeded from `src/data/{messages,folders,categories}.ts`.

This is great for prototyping and demos — **but every device starts with seeded mock data and changes never sync.** v1.1 replaces this with Lovable Cloud.

---

## 2. Target architecture (v1.1+)

### 2.1 Stack

- **Lovable Cloud** = Postgres + Auth + Storage + Edge Functions (no external accounts; never mention Supabase to end users)
- **TanStack Query** for server cache, optimistic updates, retries
- **Zustand stays** for ephemeral UI state only (selection, pane sizes, open compose window) — never for server data
- **Edge functions** for: scheduled send, snooze wake-up, rule executor, inbound mail webhook (when provider integration ships)

### 2.2 Data flow

```
┌──────────────┐    useQuery / useMutation     ┌──────────────────┐
│  Components  │ ───────────────────────────▶ │  TanStack Query  │
└──────────────┘                              └────────┬─────────┘
       ▲                                                │
       │ Zustand (UI state only)                        ▼
       │                                       ┌──────────────────┐
       │                                       │  Cloud client    │
       │                                       │  (typed RPC/REST)│
       │                                       └────────┬─────────┘
       │                                                ▼
       │                                       ┌──────────────────┐
       │                                       │  Postgres + RLS  │
       │                                       │  Auth, Storage,  │
       │                                       │  Edge Functions  │
       │                                       └──────────────────┘
```

---

## 3. Database schema

All tables are RLS-scoped to `auth.uid()`. User roles use a separate `user_roles` table (never store roles on profiles — that's a privilege-escalation vector).

### `profiles`
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | references `auth.users(id)` on delete cascade |
| `display_name` | text | |
| `avatar_url` | text | |
| `created_at` | timestamptz | default `now()` |

### `user_roles`
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `user_id` | uuid | references `auth.users(id)` |
| `role` | `app_role` enum (`admin`, `member`) | |
| unique `(user_id, role)` | | |

### `folders`
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `user_id` | uuid | RLS owner |
| `name` | text | |
| `system` | bool | true for inbox/sent/etc. |
| `parent_id` | uuid nullable | for nesting |

### `categories`
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `user_id` | uuid | RLS owner |
| `name` | text | |
| `color` | text | semantic token name |

### `threads`
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `user_id` | uuid | |
| `subject` | text | |
| `participant_emails` | text[] | |
| `last_received_at` | timestamptz | |
| `unread_count` | int | denormalized |
| `has_attachments` | bool | denormalized |
| `is_flagged` | bool | denormalized |
| `folder_id` | uuid | references `folders` |

### `messages`
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `user_id` | uuid | |
| `thread_id` | uuid | references `threads` |
| `folder_id` | uuid | references `folders` |
| `subject` | text | |
| `preview` | text | |
| `body_html` | text | |
| `sender_name` | text | |
| `sender_email` | text | |
| `recipients` | jsonb | array of `{name, email}` |
| `cc` | jsonb | |
| `bcc` | jsonb | |
| `received_at` | timestamptz | |
| `is_read` | bool | |
| `is_flagged` | bool | |
| `is_pinned` | bool | |
| `has_attachments` | bool | |
| `importance` | text | `low`/`normal`/`high` |
| `category_ids` | uuid[] | |
| `snoozed_until` | timestamptz nullable | |
| `scheduled_for` | timestamptz nullable | |
| `is_draft` | bool | |
| `is_focused` | bool | |
| `has_mentions` | bool | |
| `trust_verified` | bool | |
| `in_reply_to_id` | uuid nullable | |

Indexes: `(user_id, folder_id, received_at desc)`, `(thread_id)`, `(user_id, is_read) where is_read = false`.

### `attachments`
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `message_id` | uuid | references `messages` |
| `user_id` | uuid | RLS |
| `name` | text | |
| `size` | bigint | |
| `mime` | text | |
| `storage_path` | text | path in Cloud Storage bucket |

### `rules`
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `user_id` | uuid | |
| `name` | text | |
| `enabled` | bool | |
| `conditions` | jsonb | array per type spec |
| `actions` | jsonb | array per type spec |

### `templates`, `signatures`
Straightforward CRUD per user.

### `user_preferences`
One row per user; mirrors the `UserPreferences` type (density, reading pane, theme, focused inbox, default reply, notifications jsonb, OOO jsonb, shortcuts enabled).

### `saved_searches`
| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `user_id` | uuid | |
| `name` | text | |
| `query` | text | |
| `filters` | jsonb | |

---

## 4. Row-Level Security

Every table has `enable row level security`. The standard policy pattern:

```sql
create policy "owner can read" on messages
  for select to authenticated
  using (user_id = auth.uid());

create policy "owner can insert" on messages
  for insert to authenticated
  with check (user_id = auth.uid());

create policy "owner can update" on messages
  for update to authenticated
  using (user_id = auth.uid());

create policy "owner can delete" on messages
  for delete to authenticated
  using (user_id = auth.uid());
```

For admin-only tables, use a `has_role()` security-definer function (per the user-roles pattern in CLAUDE.md) to avoid recursive RLS.

---

## 5. Storage

- **Bucket**: `mail-attachments` (private)
- Path convention: `{user_id}/{message_id}/{attachment_id}-{filename}`
- Access via **signed URLs** (default 5 min TTL) — never public
- Upload from compose: client → signed upload URL → bucket → write `attachments` row

---

## 6. Edge Functions

| Function | Trigger | Purpose |
|----------|---------|---------|
| `send-message` | client invocation | Validate, persist, hand off to provider (or move to Sent if mock) |
| `schedule-send-tick` | cron (every minute) | Find messages where `scheduled_for <= now()` and `is_draft = true`, send them |
| `snooze-wake-tick` | cron (every minute) | Find messages where `snoozed_until <= now()` and folder=`snoozed`, move back to inbox |
| `apply-rules` | trigger on `messages` insert | Run user's enabled rules against the new message |
| `inbound-webhook` (v1.2) | HTTP from provider | Receive new mail from Microsoft Graph / Resend / Postmark, insert rows |

---

## 7. API contracts (TanStack Query hooks)

Each Zustand mutation today maps 1:1 to a future hook:

```ts
// Reads
useMessages(folderId)               // useQuery
useThread(threadId)                 // useQuery
useFolders()                        // useQuery
useUserPreferences()                // useQuery

// Writes
useToggleRead()                     // useMutation -> optimistic patch
useToggleFlag()                     // useMutation
useArchive()                        // useMutation -> snackbar with undo
useMoveTo(folderId)                 // useMutation
useSnooze(untilIso)                 // useMutation
useSendMessage()                    // useMutation -> calls send-message edge fn
useSaveDraft()                      // useMutation -> debounced
```

**Pattern**: optimistic update on cache → call edge function or RPC → on error, rollback + toast.

---

## 8. Auth

- Email + password (default)
- Google OAuth (managed by Cloud)
- Apple Sign-In (managed)
- Session via Cloud Auth, persisted in client; `_app.tsx` route gate redirects to `/auth` if no session
- `profiles` row auto-created via DB trigger on `auth.users` insert

---

## 9. Migration plan (Zustand → Cloud)

1. Enable Lovable Cloud (`supabase` enabled under the hood, but never named to users)
2. Create migrations for all tables above + RLS policies + triggers
3. Build `src/lib/cloud.ts` — typed client wrapper
4. Add TanStack Query provider in `__root.tsx` (fresh QueryClient per request via router context — never module-level singleton)
5. Replace each Zustand action with a mutation hook, one folder/feature at a time:
   - Phase 1: read-only — list messages from DB, mutations still local
   - Phase 2: write-through — mutations hit DB, Zustand removed for that domain
   - Phase 3: real-time — subscribe to Postgres changes for inbox updates
6. Migrate seeded mock data to a one-time per-user seed edge function (so demos still work)
7. Delete the per-domain Zustand store once all hooks are live

---

## 10. Real mail provider integration (v1.2)

**Recommendation**: Microsoft Graph first.

- Broadest enterprise coverage (Outlook + Exchange Online)
- Webhook-based change notifications (no polling)
- OAuth 2.0 with delegated permissions
- Threading and folder semantics map cleanly to our schema

Gmail API is a fast-follow. Generic IMAP/SMTP as a long tail (more complex, less reliable webhooks).

The provider integration lives entirely in edge functions — the client never talks directly to the mail provider. This keeps tokens server-side and lets us swap providers per tenant.
