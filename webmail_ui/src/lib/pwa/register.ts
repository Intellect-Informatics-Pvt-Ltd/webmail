/**
 * PSense Mail — Service Worker registration + lifecycle manager.
 *
 * Wraps `workbox-window` for ergonomic SW registration:
 *   - Registers `/sw.js` when the browser supports it
 *   - Fires `onNeedRefresh()` when a new SW version is waiting to activate
 *   - Fires `onOfflineReady()` when the SW has precached the shell
 *   - Fires `onRegistered(reg)` after successful registration (for push subscription)
 *   - Fires `onMessage(data)` when the SW posts a message (e.g., DELTA_SYNC_REQUESTED)
 *   - Returns `updateSW()` — call to skip waiting and reload with the new version
 *
 * Registration is intentionally deferred to after `load` so it never
 * competes with critical page resources.
 */

import { Workbox, messageSW } from "workbox-window";

export interface RegisterSWOptions {
  onNeedRefresh?: () => void;
  onOfflineReady?: () => void;
  onRegistered?: (registration: ServiceWorkerRegistration) => void;
  onRegisteredSW?: (swUrl: string, registration: ServiceWorkerRegistration) => void;
  onRegisterError?: (error: unknown) => void;
  onMessage?: (data: unknown) => void;
}

export type UpdateSWFn = (reloadPage?: boolean) => Promise<void>;

/**
 * Register the service worker and return an `updateSW` function.
 *
 * @returns A function that, when called, tells the waiting SW to skip waiting.
 *          If `reloadPage` is true (default), the page reloads after the SW activates.
 */
export function registerSW(options: RegisterSWOptions = {}): UpdateSWFn {
  const {
    onNeedRefresh,
    onOfflineReady,
    onRegistered,
    onRegisterError,
    onMessage,
  } = options;

  if (typeof window === "undefined" || !("serviceWorker" in navigator)) {
    return async () => {};
  }

  const wb = new Workbox("/sw.js", { scope: "/" });

  // Message handler — SW can post messages to the page.
  wb.addEventListener("message", (event) => {
    onMessage?.(event.data);
  });

  let _needsRefresh = false;

  // A new SW is installed and waiting to take over.
  wb.addEventListener("waiting", () => {
    _needsRefresh = true;
    onNeedRefresh?.();
  });

  // The SW has successfully precached the app shell.
  wb.addEventListener("activated", (event) => {
    if (!event.isUpdate) {
      onOfflineReady?.();
    }
  });

  // SW registered successfully.
  wb.addEventListener("registered", (event) => {
    if (event.registration) {
      onRegistered?.(event.registration);
    }
  });

  // updateSW: send SKIP_WAITING to the waiting SW, optionally reload.
  const updateSW: UpdateSWFn = async (reloadPage = true) => {
    if (_needsRefresh) {
      wb.addEventListener("controlling", () => {
        if (reloadPage) window.location.reload();
      });
      await messageSW(wb.getSW()!, { type: "SKIP_WAITING" });
    }
  };

  // Defer registration until the page is fully loaded.
  const doRegister = async () => {
    try {
      await wb.register();
    } catch (error) {
      onRegisterError?.(error);
    }
  };

  if (document.readyState === "complete") {
    void doRegister();
  } else {
    window.addEventListener("load", () => void doRegister(), { once: true });
  }

  return updateSW;
}

/**
 * Request a one-shot background sync tag from the active SW registration.
 * Safe to call even when the Background Sync API is unsupported — degrades gracefully.
 */
export async function requestBackgroundSync(tag: string): Promise<void> {
  if (!("serviceWorker" in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    if ("sync" in reg) {
      // @ts-expect-error Background Sync API typings are not in lib.dom yet
      await reg.sync.register(tag);
    }
  } catch {
    // Background sync not supported or permission denied — fall back to
    // polling in the app (already implemented in outbox.ts / delta.ts)
  }
}

/**
 * Subscribe to Web Push notifications.
 *
 * @param vapidPublicKey — base64url-encoded VAPID public key from the server.
 * @returns The PushSubscription JSON, or null if unsupported / denied.
 *
 * TODO Phase 4: wire this to the backend's push subscription endpoint.
 */
export async function subscribeToPush(vapidPublicKey: string): Promise<PushSubscription | null> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return null;

  const permission = await Notification.requestPermission();
  if (permission !== "granted") return null;

  try {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: _urlBase64ToUint8Array(vapidPublicKey),
    });
    return sub;
  } catch {
    return null;
  }
}

function _urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from(rawData, (c) => c.charCodeAt(0));
}
