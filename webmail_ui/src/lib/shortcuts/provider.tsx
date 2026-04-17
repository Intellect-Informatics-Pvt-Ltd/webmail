/**
 * PSense Mail — ShortcutProvider.
 *
 * Mount once at the root. Attaches the global keydown listener and
 * registers the default application-wide shortcuts.
 *
 * Route-level or modal-level shortcuts are registered by their own
 * components via `useShortcut()`.
 */

import { type ReactNode, useEffect } from "react";
import { attachGlobalListener, detachGlobalListener, registerShortcut, unregisterShortcut } from "./registry";

interface ShortcutProviderProps {
  children: ReactNode;
  /** If false, global listener is not attached (useful in tests). */
  enabled?: boolean;
}

export function ShortcutProvider({ children, enabled = true }: ShortcutProviderProps) {
  useEffect(() => {
    if (!enabled) return;
    attachGlobalListener();
    return () => detachGlobalListener();
  }, [enabled]);

  return <>{children}</>;
}
