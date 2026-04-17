/**
 * PSense Mail — usePWAUpdate hook.
 *
 * Exposes the SW update lifecycle to the UI:
 *   needsRefresh   — true when a new SW version is waiting; show a "Reload to update" banner.
 *   isOfflineReady — true when the shell is fully precached and the app is usable offline.
 *   updateSW()     — call to activate the waiting SW and reload the page.
 *   dismissUpdate()— call to hide the banner without reloading (user can reload later).
 *
 * Also forwards SW messages (DELTA_SYNC_REQUESTED) to a caller-supplied callback.
 */

import { useState, useEffect, useRef } from "react";
import { registerSW, type UpdateSWFn } from "./register";

export interface PWAUpdateState {
  needsRefresh: boolean;
  isOfflineReady: boolean;
  updateSW: (reloadPage?: boolean) => Promise<void>;
  dismissUpdate: () => void;
}

export function usePWAUpdate(
  onSWMessage?: (data: unknown) => void,
): PWAUpdateState {
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const [isOfflineReady, setIsOfflineReady] = useState(false);
  const updateSWRef = useRef<UpdateSWFn>(async () => {});

  useEffect(() => {
    if (typeof window === "undefined") return;

    const updateSW = registerSW({
      onNeedRefresh: () => setNeedsRefresh(true),
      onOfflineReady: () => setIsOfflineReady(true),
      onMessage: (data) => {
        onSWMessage?.(data);
      },
      onRegisterError: (err) => {
        console.warn("[PSense Mail SW] Registration failed:", err);
      },
    });

    updateSWRef.current = updateSW;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    needsRefresh,
    isOfflineReady,
    updateSW: (reloadPage = true) => updateSWRef.current(reloadPage),
    dismissUpdate: () => setNeedsRefresh(false),
  };
}
