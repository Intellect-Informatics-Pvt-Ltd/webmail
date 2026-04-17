# PSense Mail — Project Documentation

This folder contains the living plans, specs, and architecture docs for **PSense Mail**, an enterprise mail workspace built on TanStack Start + Tailwind v4 + shadcn/ui, branded as PSense.ai.

## Index

| # | Document | Purpose |
|---|----------|---------|
| 01 | [BRD](./01-brd.md) | Business requirements, vision, users, scope, success metrics |
| 02 | [Implementation Plan](./02-implementation-plan.md) | What's built, what's pending, build order, milestones |
| 03 | [Design System](./03-design-system.md) | Brand tokens, typography, density, components, a11y |
| 04 | [Backend & Data Architecture](./04-backend-architecture.md) | Future Cloud schema, RLS, edge functions, storage, API contracts |

## Conventions

- **Tech stack**: TanStack Start v1, React 19, Vite 7, Tailwind v4 (`oklch` tokens via `src/styles.css`), shadcn/ui, Zustand, Tiptap, lucide-react, `@tanstack/react-virtual`.
- **Backend (today)**: 100% client-side. Zustand + `localStorage` (`psense-mail-data`, `psense-compose`, `psense-ui`).
- **Backend (target)**: Lovable Cloud — Postgres + Auth + Storage + Edge Functions, with TanStack Query for data access.
- **Branding**: Never mention Supabase to end users — it's "Lovable Cloud" or "PSense backend."
- **Design tokens only**: No hardcoded colors in components; everything flows through `src/styles.css`.

## How to update these docs

Edit the markdown files in place. They're versioned with the code, so any PR can update both code and plan together. When a major surface ships (e.g. Calendar), bump the relevant doc and tick the checkbox in `02-implementation-plan.md`.
