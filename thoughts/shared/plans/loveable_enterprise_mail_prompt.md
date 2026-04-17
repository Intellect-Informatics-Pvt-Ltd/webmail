# Opinionated Loveable Prompt
## Enterprise Mail Interface
### React + Vite + TypeScript + Tailwind + shadcn/ui + Zustand + TanStack Router

Use the following prompt in Loveable.

---

Build a **modern enterprise web mail client** as a **React + Vite** application using **TypeScript**, **Tailwind CSS**, **shadcn/ui**, **Zustand** for client state, and **TanStack Router** for routing.

This must be a **real interactive front-end application shell**, not a landing page and not a single static screen. The result should feel like a **production-grade enterprise mail workspace** inspired by the usability of modern Outlook, but not visually copied from it.

The application should be **component-driven, composable, scalable, keyboard-friendly, and enterprise-ready**, with realistic mock data and polished UX throughout.

---

## Core objective

Create a desktop-first web mail experience optimized for high-volume enterprise usage. The product should support:

- inbox triage
- advanced search
- threaded reading
- rich text composition
- folder and category organization
- bulk actions
- keyboard productivity
- settings and preferences
- believable empty, loading, and error states
- future API integration without major restructuring

This should feel like a tool that an operations lead, recruiter, account manager, executive assistant, or enterprise employee could genuinely use all day.

---

## Required stack

Use exactly this stack unless absolutely necessary otherwise:

- **React**
- **Vite**
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui**
- **Zustand**
- **TanStack Router**
- **lucide-react** for icons
- **react-hook-form** for forms where useful
- **zod** for schema validation where useful
- **@tanstack/react-virtual** or an equivalent lightweight approach for message list performance if needed
- **Tiptap** or another rich text editor suitable for email composition

Do not use Redux.
Do not use Next.js.
Do not use Material UI.
Do not generate a generic dashboard template.

---

## Product and UX direction

Design a **premium enterprise SaaS mail workspace** with these characteristics:

- clean, restrained, modern, and dense enough for real work
- not flashy, not gamified, not consumer-cute
- strong hierarchy and scanability
- subtle elevation
- crisp borders
- accessible contrast
- thoughtful hover, active, focus, selected, and disabled states
- responsive, but optimized for large laptop and desktop use
- usable in light mode and dark mode
- visually coherent with a modern Microsoft 365 / enterprise productivity sensibility, but still original

Prioritize:
- triage speed
- clarity
- composability
- accessibility
- extensibility

---

## Application information architecture

Implement the app as a mail workspace with the following major areas:

### Global shell
- top header
- app left rail
- mail sidebar
- central message list
- reading pane
- overlays/drawers/modals
- command palette
- settings surfaces

### Main routes using TanStack Router
Create these routes:

- `/mail/inbox`
- `/mail/focused`
- `/mail/other`
- `/mail/sent`
- `/mail/drafts`
- `/mail/archive`
- `/mail/flagged`
- `/mail/snoozed`
- `/mail/deleted`
- `/mail/search`
- `/mail/folder/$folderId`
- `/mail/category/$categoryId`
- `/settings/mail`
- `/settings/preferences`
- `/rules`
- `/templates`

Use route-based screens where it makes sense, but preserve a cohesive app-shell experience.

---

## Layout requirements

The default layout should be a **three-pane mail UI**:

1. **mail navigation/sidebar**
2. **message list**
3. **reading pane**

Also support:
- reading pane on the right
- reading pane at the bottom
- hidden reading pane / list-focused mode

Support:
- resizable panes
- collapsible sidebar
- density modes: compact, comfortable, spacious
- sticky toolbar/header regions where appropriate

Do not create a simplistic fixed-width layout.
Make the layout feel like a real work product.

---

## Feature set to include

## 1. App shell and navigation

Build:
- global top bar with:
  - global search
  - quick actions
  - notifications placeholder
  - settings shortcut
  - help shortcut
  - user avatar/profile dropdown

- left app rail with:
  - Mail
  - Calendar placeholder
  - Contacts placeholder
  - Tasks placeholder

- mail sidebar containing:
  - New mail button
  - Favorites section
  - Inbox
  - Focused
  - Other
  - Drafts
  - Sent
  - Archive
  - Snoozed
  - Flagged
  - Deleted
  - Junk
  - custom folders
  - categories / labels
  - storage usage or account info placeholder

Add support for:
- favorite folders
- unread counts
- drag-and-drop folder ordering feel
- context menus on folders
- create / rename folder dialogs
- category manager entry point

---

## 2. Inbox and message list

Create a high-quality message list with realistic enterprise behavior.

Each row should support:
- sender
- sender avatar/initials
- subject
- preview snippet
- timestamp
- unread styling
- selected styling
- flagged state
- pinned state
- attachment indicator
- category chips
- importance indicator
- meeting/event or file markers if present
- hover quick actions

Support:
- row checkbox selection
- multi-select
- bulk action toolbar
- keyboard navigation between rows
- grouped list sections:
  - Today
  - Yesterday
  - Earlier this week
  - Older

Provide tabs or view controls for:
- All
- Unread
- Focused
- Other
- Attachments
- Mentions

Provide message-level quick actions:
- archive
- delete
- mark read/unread
- flag/unflag
- pin/unpin
- snooze
- move
- categorize

Provide bulk actions:
- archive
- delete
- move
- categorize
- mark read
- mark unread
- flag
- clear flag
- snooze

Support display density settings:
- compact
- comfortable
- spacious

Use realistic list interaction patterns and visual hierarchy.
Do not make the list look like a social feed.

---

## 3. Reading pane and thread view

The reading pane should feel substantial and enterprise-grade.

Display:
- subject
- sender and recipients
- cc / bcc expansion
- timestamp
- categories
- message status / metadata
- trust/security badge placeholder
- thread indicators
- attachment strip
- related actions

Include an action toolbar with:
- Reply
- Reply all
- Forward
- Archive
- Delete
- Move
- Categorize
- Flag
- Snooze
- More actions

Support conversation/thread view:
- show multiple emails in the same thread
- collapsible earlier messages
- quoted content styling
- trimmed message sections
- expand all / collapse all
- per-message actions within a thread

Attachment area:
- file cards
- type icon
- size
- preview placeholder
- download placeholder
- inline image preview placeholder where useful

Optional side metadata drawer:
- message headers placeholder
- labels/categories
- folder location
- received time
- thread id placeholder
- retention/security placeholder

---

## 4. Search

Search must be treated as a first-class product surface, not just a text box.

Implement:
- prominent global search bar in top header
- autosuggest dropdown
- recent searches
- search tips/syntax helper
- advanced search panel
- dedicated search results page

Search should cover:
- messages
- people
- files/attachments placeholders

Advanced search filters:
- sender
- recipient
- subject
- keyword/body text
- date range
- has attachment
- unread
- flagged
- category
- folder
- importance
- from me
- mentions me

Search results page should include:
- left-side facets
- sort options
- active filter chips
- results summary
- result rows styled differently from the inbox if needed
- empty results state
- saved search option

Do not treat search as an afterthought.

---

## 5. Compose experience

Build a premium compose flow with both:
- floating compose window
- expanded full-screen compose mode

Fields:
- To
- Cc
- Bcc
- Subject

Recipient input behavior:
- chip-based recipients
- validation
- avatar initials
- invalid state
- suggestion dropdown placeholder
- overflow handling for many recipients

Rich text editor requirements:
- bold
- italic
- underline
- strikethrough
- font size
- text color
- highlight
- alignment
- bulleted list
- numbered list
- quote block
- hyperlink
- undo/redo
- clear formatting
- code block optional
- table placeholder support optional
- inline image placeholder
- attachment placeholder

Compose actions:
- send
- schedule send
- save draft
- discard
- pop out / full-screen
- attach file
- insert signature
- insert template placeholder

Compose UX details:
- autosave drafts indicator
- unsaved changes warning
- attachment upload progress UI
- disabled sending state
- error banner placeholder
- keyboard shortcuts for send and formatting where practical

Use a real editor integration approach, not a fake textarea pretending to be rich text.

---

## 6. Organization and productivity features

Include interfaces for:
- move to folder
- copy to folder
- categories manager
- snooze picker
- sweep / cleanup modal
- follow-up / reminder placeholder
- rules center
- templates manager
- signature manager
- keyboard shortcuts modal
- command palette

Rules center UI should support rule cards such as:
- from sender → move to folder
- if has attachment → categorize
- if subject contains keyword → mark important
- older than X → archive placeholder
- newsletters → move to low priority folder placeholder

The UI can be mock-powered, but it should feel product-ready.

---

## 7. Settings and preferences

Create robust settings screens.

Mail settings should include:
- reading pane placement
- conversation threading on/off
- focused inbox on/off
- density
- default sort
- preview line count
- swipe/archive placeholder if helpful
- notifications preferences
- signatures
- out-of-office placeholder
- appearance theme
- keyboard shortcut help
- default reply behavior
- schedule send defaults placeholder

Use a settings layout that is scalable for future enterprise options.

---

## 8. States and resilience

Every important surface should have:
- empty state
- loading skeleton
- error state
- zero results state
- optimistic/toast feedback where relevant

Examples:
- empty inbox
- no message selected
- no search results
- failed to load thread
- failed to send draft
- no attachments
- no custom folders yet
- no rules yet

Add unobtrusive toast notifications for actions like:
- message archived
- moved to folder
- draft saved
- rule created
- changes undone

---

## 9. Accessibility and keyboard support

This app must feel like it was built for serious daily usage.

Include:
- visible focus states
- full keyboard navigability
- semantic roles and ARIA-friendly primitives
- accessible dialogs, menus, comboboxes, listboxes, tabs, and command menus
- good contrast
- hover not required for primary interaction
- support for keyboard shortcuts like:
  - compose
  - reply
  - archive
  - search focus
  - next/previous message
  - toggle read/unread
  - help modal

Add a keyboard shortcuts help modal.

---

## 10. Theming and visual system

Implement a reusable design system foundation.

Define or structure:
- semantic color tokens
- surface/background tokens
- border tokens
- spacing scale
- typography scale
- radius scale
- shadow/elevation tokens
- density variants
- light and dark themes

Ensure shadcn/ui components are customized enough that the UI does not look like default boilerplate.

---

## Data and state modeling

Use **Zustand** stores for app state and mail state.

Create realistic TypeScript models for:
- MailMessage
- MailThread
- MailFolder
- MailCategory
- MailRecipient
- MailAttachment
- MailRule
- SavedSearch
- UserPreferences
- ComposeDraft

Message model should include fields like:
- id
- threadId
- folderId
- subject
- preview
- bodyHtml or editor content
- sender
- recipients
- cc
- bcc
- receivedAt
- isRead
- isFlagged
- isPinned
- hasAttachments
- importance
- categories
- snoozedUntil
- isDraft
- isFocused
- hasMentions
- attachments

State should support:
- selected folder
- selected thread/message
- search query
- active filters
- pane sizes
- layout mode
- density
- compose windows
- toasts
- preferences

Mock data should be realistic and varied:
- unread and read emails
- internal and external senders
- attachments
- threaded conversations
- flagged items
- drafts
- scheduled draft placeholders
- categories

---

## Recommended project structure

Use a clean structure similar to:

- `src/app`
- `src/routes`
- `src/components/layout`
- `src/components/mail`
- `src/components/search`
- `src/components/compose`
- `src/components/settings`
- `src/components/rules`
- `src/components/common`
- `src/components/ui`
- `src/stores`
- `src/hooks`
- `src/lib`
- `src/types`
- `src/data/mock`
- `src/features/...` if preferred for domain grouping

Favor modularity.
Do not dump everything into a few giant files.

---

## shadcn/ui expectations

Use shadcn/ui thoughtfully for:
- button
- input
- textarea if needed
- dialog
- drawer
- popover
- dropdown menu
- sheet
- tabs
- tooltip
- badge
- breadcrumb
- avatar
- scroll area
- separator
- command
- form
- select
- checkbox
- radio group
- switch
- calendar/date picker patterns where helpful

Do not leave the app looking like raw shadcn demo code.
Customize it into a coherent enterprise mail product.

---

## Interaction quality bar

The app should include polished microinteractions such as:
- hover quick actions on mail rows
- smooth pane resizing
- subtle selection transitions
- compose window expand/collapse
- command palette opening
- filter chip selection
- toast undo actions

Keep animations subtle and fast.
Do not over-animate.

---

## What to avoid

Do not:
- make this a marketing site
- make this a generic admin dashboard
- build only one screen
- use lorem ipsum everywhere
- create fake giant graphs unrelated to mail
- overuse gradients
- over-round everything
- prioritize aesthetics over usability
- make the inbox sparse and toy-like
- ignore loading/error/empty states
- skip search, rules, settings, or organization features
- skip accessibility
- skip realistic mail workflows

---

## Deliverables

Generate:
1. a full React + Vite + TypeScript project structure
2. reusable components
3. route setup with TanStack Router
4. Zustand stores and mock state
5. realistic seed data
6. multiple polished screens and flows
7. an interactive inbox experience
8. advanced search experience
9. rich compose experience
10. settings/rules/templates surfaces

At minimum, the generated app should allow someone to:
- navigate folders
- view inbox list
- open a thread
- search mail
- filter messages
- compose a new message
- save a draft locally
- perform bulk actions
- open settings
- explore rules/templates UI

---

## Final implementation guidance

Think like a senior product engineer and systems-minded designer building the front-end foundation for an enterprise mail product.

The output should feel:
- credible
- modular
- extendable
- keyboard-friendly
- visually polished
- information-dense
- production-shaped

Do not produce a superficial concept.
Produce a realistic, structured, interactive enterprise mail client front end with strong component boundaries and scalable architecture.
