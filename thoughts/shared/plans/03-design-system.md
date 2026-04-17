# PSense Mail — Design System

**Status**: v1.0 implemented in `src/styles.css`
**Last updated**: 2026-04-17

---

## 1. Brand identity

- **Product name**: PSense Mail
- **Parent brand**: PSense.ai
- **Voice**: Calm, focused, professional — never playful or whimsical
- **Logo**: `src/assets/psense-logo.svg` — purple wordmark; used in sidebar header, command palette, and the mandatory "Powered by PSense" footer on every screen

---

## 2. Color tokens

All colors are defined as **`oklch`** in `src/styles.css` and exposed as semantic CSS variables. **Never hardcode hex/rgb in components.**

### Core palette (light)

| Token | Purpose | Approx. hex |
|-------|---------|-------------|
| `--background` | App background | `#FFFFFF` |
| `--foreground` | Primary text | `#1A1024` |
| `--card` / `--popover` | Elevated surfaces | `#FFFFFF` |
| `--primary` | Brand purple — CTAs, focus, active states | `#7B49FB` |
| `--primary-foreground` | Text on primary | `#FFFFFF` |
| `--secondary` | Subtle surfaces | very light purple |
| `--muted` / `--muted-foreground` | De-emphasized text/surfaces | greys |
| `--accent` | Hover states | very light purple |
| `--destructive` | Delete actions | red |
| `--success` / `--warning` / `--info` | Status colors | green / amber / blue |
| `--border` / `--input` / `--ring` | Borders, inputs, focus ring | subtle purples |

### Sidebar / rail tokens

The mail sidebar uses **deep purple** (HSL 262 60% 12% → oklch). The rail (left workspace switcher) shares the same dark token family.

| Token | Purpose |
|-------|---------|
| `--sidebar` | Sidebar background (dark purple) |
| `--sidebar-foreground` | Sidebar text (off-white) |
| `--sidebar-primary` | Active item background |
| `--sidebar-primary-foreground` | Active item text |
| `--sidebar-accent` | Hover background |
| `--sidebar-accent-foreground` | Hover text |
| `--sidebar-border` | Separators inside sidebar |
| `--rail` / `--rail-foreground` / `--rail-active` | Workspace rail tokens |

Dark theme overrides every token in the `.dark` block — verify contrast on every new surface.

---

## 3. Typography

| Role | Font stack | Size / weight |
|------|------------|---------------|
| UI (default) | System sans (`-apple-system, Segoe UI, Inter, sans-serif`) | 14px / 400 |
| Headings | Same | 16–24px / 600 |
| Code / mono | System mono | 13px / 400 |
| Email body (compose, reading) | System sans, larger line-height | 15px / 1.6 |

Avoid loading custom web fonts unless brand requires it — keeps TTI low.

---

## 4. Spacing & density

Three density modes controlled via `useUIStore` and applied through CSS classes / Tailwind utilities:

| Mode | Row height | Padding | Use case |
|------|-----------|---------|----------|
| `compact` | 36px | tight | Power users, large monitors |
| `comfortable` (default) | 52px | medium | Most users |
| `spacious` | 68px | generous | Touch / accessibility |

Spacing scale follows Tailwind's default 4px base unit. Use multiples of 4 for all margins/padding.

---

## 5. Layout

```
┌─────────────────────────────────────────────────────────────┐
│ App header (logo, search, compose, notifications, avatar)   │
├──┬──────────────┬──────────────────────────┬────────────────┤
│  │              │                          │                │
│ R│  Mail        │  Message list            │  Reading pane  │
│ a│  sidebar     │  (virtualized)           │  (right/bottom │
│ i│  (folders,   │                          │   /off)        │
│ l│  favorites,  │                          │                │
│  │  categories) │                          │                │
│  │              │                          │                │
├──┴──────────────┴──────────────────────────┴────────────────┤
│ Powered by PSense (mandatory footer)                        │
└─────────────────────────────────────────────────────────────┘
```

- **Rail**: 56px fixed, dark
- **Mail sidebar**: 240–280px, resizable, collapsible, dark purple
- **Message list**: flex, min 320px
- **Reading pane**: resizable; right (default), bottom, or off
- **Footer**: 32px, always visible

---

## 6. Component principles

- **Use shadcn primitives** (`Button`, `Dialog`, `Popover`, `DropdownMenu`, `Tooltip`, `Command`, `ScrollArea`, etc.) — never roll your own focus traps or ARIA from scratch.
- **Variants over props sprawl**: extend with `cva` when a component needs >2 style modes.
- **Icons**: `lucide-react` only. 16px in dense UI, 20px elsewhere.
- **Motion**: Subtle. Use `framer-motion` only for: compose window open/close, command palette, toast in/out. No bouncy springs.
- **Empty states**: every list surface has an empty state with an icon, headline, and optional CTA.
- **Loading**: skeleton rows for lists; spinner only for inline actions.

---

## 7. Accessibility

- **Visible focus rings** on every interactive element via `--ring`
- **Full keyboard support**: tab order matches visual order; arrow keys + `j/k` in lists
- **ARIA via shadcn primitives** — don't manually wire `aria-*` unless extending
- **Color contrast**: all text/background pairs ≥ WCAG AA (4.5:1 for body, 3:1 for large)
- **Screen reader labels** on every icon-only button (`aria-label` or `<span class="sr-only">`)
- **Keyboard shortcuts modal** (`?`) lists every shortcut so users can discover them
- **Reduced motion**: respect `prefers-reduced-motion` — disable framer animations

---

## 8. Theming rules

- **One source of truth**: `src/styles.css` `:root` (light) and `.dark` (dark)
- **No inline styles** for color, spacing, or typography
- **No Tailwind color utilities like `bg-purple-600`** — use `bg-primary`, `bg-sidebar`, etc.
- **When adding a new semantic color**, add the token to `@theme inline`, `:root`, and `.dark` in a single edit

---

## 9. Component inventory (current)

| Surface | Component(s) |
|---------|--------------|
| Shell | `AppHeader`, `AppRail`, `MailSidebar`, `PoweredByFooter` |
| Mail list | `MailWorkspace`, `MessageList`, `MessageRow` |
| Reading | `ReadingPane` |
| Compose | `ComposeWindow` (Tiptap) |
| Overlays | `GlobalOverlays` (⌘K palette + `?` shortcuts) |
| Brand | `PSenseLogo` |
| Theming | `ThemeManager` |
| Primitives | All of `src/components/ui/*` (shadcn) |

---

## 10. Don'ts

- ❌ No hardcoded colors (`#7B49FB`, `bg-purple-500`, `text-white`)
- ❌ No custom fonts beyond system stack without explicit approval
- ❌ No third-party UI kits (MUI, Chakra, Mantine) — shadcn only
- ❌ No icon libraries other than lucide-react
- ❌ No CSS-in-JS runtime libs (styled-components, emotion) — Tailwind only
- ❌ No bouncy / playful animations — keep motion subtle and purposeful
