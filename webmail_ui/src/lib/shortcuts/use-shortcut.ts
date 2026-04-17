/**
 * PSense Mail — useShortcut hook.
 *
 * Declaratively registers a shortcut for the lifecycle of the component.
 * The shortcut is unregistered when the component unmounts.
 *
 * Usage:
 *   useShortcut({
 *     id: "archive",
 *     keys: ["e"],
 *     scope: "route",
 *     handler: () => archive(selectedIds),
 *     description: "Archive selected",
 *     category: "Mail",
 *   });
 */

import { useEffect } from "react";
import { type ShortcutDefinition, registerShortcut, unregisterShortcut } from "./registry";

export function useShortcut(def: ShortcutDefinition): void {
  useEffect(() => {
    registerShortcut(def);
    return () => unregisterShortcut(def.id);
    // Re-register if keys or handler changes (stringify compares primitives)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [def.id, def.enabled, def.scope, JSON.stringify(def.keys)]);
}
