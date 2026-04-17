/**
 * PSense Mail — Central keyboard shortcut registry.
 *
 * All keyboard shortcuts in the application are registered here via
 * `registerShortcut()`. This ensures:
 *   1. A single global listener (no listener leaks).
 *   2. The `?` shortcuts modal is always self-documenting.
 *   3. Scope stacking: modal shortcuts shadow route shortcuts which shadow global.
 *
 * Scope priority (highest first): "modal" > "route" > "global"
 *
 * Usage:
 *   // Register once (in a provider / route component):
 *   registerShortcut({ id: "compose", keys: ["c"], scope: "global",
 *     handler: () => openCompose(), description: "New message" });
 *
 *   // Deregister on unmount:
 *   unregisterShortcut("compose");
 *
 *   // Or use the hook:
 *   useShortcut({ id: "archive", keys: ["e"], handler: () => archive() });
 */

// ── Types ─────────────────────────────────────────────────────────────────────

export type ShortcutScope = "global" | "route" | "modal";

export interface ShortcutDefinition {
  /** Unique identifier used for de-registration and the shortcuts modal. */
  id: string;
  /**
   * Key combo array. Each entry is a string like:
   *   "c"         - bare letter
   *   "Meta+k"    - Command+K (⌘K on macOS)
   *   "Ctrl+k"    - Ctrl+K
   *   "Shift+?"   - Shift+?
   * The matcher normalises Meta/Ctrl via the isMac check.
   */
  keys: string[];
  /** Scope determines which shortcuts are active at any given time. */
  scope: ShortcutScope;
  handler: (event: KeyboardEvent) => void;
  /** Human-readable description for the shortcuts modal. */
  description: string;
  /** Category displayed in the shortcuts modal (defaults to "General"). */
  category?: string;
  /** If false, the shortcut appears in the modal but is disabled. */
  enabled?: boolean;
}

// ── Registry store ────────────────────────────────────────────────────────────

const _shortcuts = new Map<string, ShortcutDefinition>();
const _listeners = new Set<() => void>();

/** Subscribe to registry changes (used by the shortcuts modal). */
export function subscribeToRegistry(listener: () => void): () => void {
  _listeners.add(listener);
  return () => _listeners.delete(listener);
}

function _notify() {
  _listeners.forEach((l) => l());
}

export function registerShortcut(def: ShortcutDefinition): void {
  _shortcuts.set(def.id, { enabled: true, category: "General", ...def });
  _notify();
}

export function unregisterShortcut(id: string): void {
  _shortcuts.delete(id);
  _notify();
}

export function updateShortcut(id: string, patch: Partial<ShortcutDefinition>): void {
  const existing = _shortcuts.get(id);
  if (existing) {
    _shortcuts.set(id, { ...existing, ...patch });
    _notify();
  }
}

export function getShortcuts(): ShortcutDefinition[] {
  return Array.from(_shortcuts.values());
}

export function getShortcutsByCategory(): Record<string, ShortcutDefinition[]> {
  const result: Record<string, ShortcutDefinition[]> = {};
  for (const def of _shortcuts.values()) {
    const cat = def.category ?? "General";
    if (!result[cat]) result[cat] = [];
    result[cat].push(def);
  }
  return result;
}

// ── Key matching ──────────────────────────────────────────────────────────────

const isMac = typeof navigator !== "undefined" && /mac/i.test(navigator.platform);

/**
 * Normalise a shortcut combo string to a canonical form for matching.
 * "Meta+k" on Mac == "Ctrl+k" on Windows normalised to "cmd+k".
 */
function normalisedCombo(raw: string): string {
  return raw
    .toLowerCase()
    .replace(/meta\+/g, "cmd+")
    .replace(/control\+/g, "ctrl+")
    .replace(/ /g, "");
}

function eventToCombo(e: KeyboardEvent): string {
  const parts: string[] = [];
  if (isMac ? e.metaKey : e.ctrlKey) parts.push("cmd");
  if (e.altKey) parts.push("alt");
  if (e.shiftKey) parts.push("shift");
  parts.push(e.key.toLowerCase());
  return parts.join("+");
}

// ── Active scope stack ────────────────────────────────────────────────────────

const SCOPE_PRIORITY: Record<ShortcutScope, number> = { modal: 2, route: 1, global: 0 };

function _activeScope(): ShortcutScope {
  let max = -1;
  let active: ShortcutScope = "global";
  for (const def of _shortcuts.values()) {
    if (!def.enabled) continue;
    const p = SCOPE_PRIORITY[def.scope];
    if (p > max) { max = p; active = def.scope; }
  }
  return active;
}

// ── Global listener ───────────────────────────────────────────────────────────

let _listenerAttached = false;

function _globalKeyHandler(e: KeyboardEvent): void {
  // Ignore shortcuts when typing in inputs/textareas (except cmd-combos)
  const target = e.target as HTMLElement;
  const isInput = target?.tagName === "INPUT" || target?.tagName === "TEXTAREA" ||
    target?.isContentEditable;
  const hasModifier = e.metaKey || e.ctrlKey;

  if (isInput && !hasModifier) return;

  const combo = eventToCombo(e);
  const activeScope = _activeScope();

  for (const def of _shortcuts.values()) {
    if (!def.enabled) continue;
    // Only fire shortcuts at or above the active scope level
    if (SCOPE_PRIORITY[def.scope] < SCOPE_PRIORITY[activeScope]) continue;
    for (const key of def.keys) {
      if (normalisedCombo(key) === combo) {
        e.preventDefault();
        def.handler(e);
        return;
      }
    }
  }
}

export function attachGlobalListener(): void {
  if (_listenerAttached || typeof window === "undefined") return;
  window.addEventListener("keydown", _globalKeyHandler, { capture: true });
  _listenerAttached = true;
}

export function detachGlobalListener(): void {
  if (!_listenerAttached || typeof window === "undefined") return;
  window.removeEventListener("keydown", _globalKeyHandler, { capture: true });
  _listenerAttached = false;
}
