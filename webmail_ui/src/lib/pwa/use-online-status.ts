/**
 * PSense Mail — useOnlineStatus hook.
 *
 * Tracks `navigator.onLine` and the browser's `online` / `offline` events.
 *
 * Returns:
 *   isOnline  — true when the browser reports network connectivity.
 *   isOffline — convenience inverse.
 *   since     — ISO timestamp of the last status change (for "You've been offline for Xm" UI).
 *
 * Note: `navigator.onLine` can return `true` even when the actual request
 * would fail (e.g., captive portal, no DNS). For a more accurate signal, the
 * API client's error handling sets `isOffline` after consecutive network errors.
 * This hook is the "fast path" for immediate UI feedback.
 */

import { useState, useEffect, useCallback } from "react";

export interface OnlineStatus {
  isOnline: boolean;
  isOffline: boolean;
  since: string;
}

export function useOnlineStatus(): OnlineStatus {
  const [status, setStatus] = useState<OnlineStatus>(() => ({
    isOnline: typeof navigator !== "undefined" ? navigator.onLine : true,
    isOffline: typeof navigator !== "undefined" ? !navigator.onLine : false,
    since: new Date().toISOString(),
  }));

  const handleOnline = useCallback(() => {
    setStatus({ isOnline: true, isOffline: false, since: new Date().toISOString() });
  }, []);

  const handleOffline = useCallback(() => {
    setStatus({ isOnline: false, isOffline: true, since: new Date().toISOString() });
  }, []);

  useEffect(() => {
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [handleOnline, handleOffline]);

  return status;
}
