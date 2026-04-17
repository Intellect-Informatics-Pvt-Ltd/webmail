/**
 * PSense Mail — Service Worker (Workbox-powered).
 *
 * Compiled by vite-plugin-pwa in `injectManifest` mode.
 * Workbox replaces `self.__WB_MANIFEST` with the real precache manifest
 * at build time.
 *
 * TIERS IMPLEMENTED HERE
 * ──────────────────────
 * Tier 1 — Shell precaching:   App shell (HTML/JS/CSS) precached so that
 *           on offline load the UI paints immediately from cache.
 *
 * Tier 2 — API runtime caching:  GET /api/v1/* cached with NetworkFirst
 *           (10 s timeout). On offline, stale API response served.
 *           Max 200 entries, 7-day expiry.
 *
 * Tier 3 — Background sync queue: Failed POST/PATCH to mutating endpoints
 *           are queued and replayed when the device reconnects,
 *           even if the tab is closed.
 *
 * Tier 4 — Push notifications scaffold:  Receives push events from the
 *           backend and shows browser notifications.
 *           Full implementation: Phase 4 (requires push server key config).
 */

import { cleanupOutdatedCaches, precacheAndRoute } from "workbox-precaching";
import { registerRoute, Route } from "workbox-routing";
import { NetworkFirst, CacheFirst, StaleWhileRevalidate } from "workbox-strategies";
import { ExpirationPlugin } from "workbox-expiration";
import { CacheableResponsePlugin } from "workbox-cacheable-response";
import { BackgroundSyncPlugin } from "workbox-background-sync";
import { clientsClaim } from "workbox-core";

declare const self: ServiceWorkerGlobalScope;

// ── Lifecycle ─────────────────────────────────────────────────────────────────

// Immediately claim all clients on activate so updates take effect
// without a page reload.
self.skipWaiting();
clientsClaim();

// Remove caches from previous Workbox versions.
cleanupOutdatedCaches();

// ── Tier 1: Shell precaching ──────────────────────────────────────────────────

// self.__WB_MANIFEST is replaced by the Workbox build tool with the list of
// hashed assets emitted by Vite.
precacheAndRoute(self.__WB_MANIFEST);

// ── Tier 2: API runtime caching ───────────────────────────────────────────────

// GET requests to the API are served NetworkFirst with a 10 s network timeout.
// Successful responses are cached for 7 days / 200 entries.
const apiGetRoute = new Route(
  ({ request, url }) =>
    request.method === "GET" && url.pathname.startsWith("/api/v1/"),
  new NetworkFirst({
    cacheName: "psense-api-v1",
    networkTimeoutSeconds: 10,
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({
        maxEntries: 200,
        maxAgeSeconds: 7 * 24 * 60 * 60, // 7 days
        purgeOnQuotaError: true,
      }),
    ],
  }),
);
registerRoute(apiGetRoute);

// Static assets — fonts, images from Google Fonts, CDN — CacheFirst.
const staticAssetsRoute = new Route(
  ({ url }) =>
    url.origin !== self.location.origin &&
    (url.pathname.match(/\.(woff2?|ttf|eot|svg|png|jpg|webp|ico)$/) !== null),
  new CacheFirst({
    cacheName: "psense-static-assets",
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxEntries: 60, maxAgeSeconds: 30 * 24 * 60 * 60 }),
    ],
  }),
);
registerRoute(staticAssetsRoute);

// App navigation: SPA shell — StaleWhileRevalidate so routes always render.
const navigationRoute = new Route(
  ({ request }) => request.mode === "navigate",
  new StaleWhileRevalidate({
    cacheName: "psense-navigation",
    plugins: [new CacheableResponsePlugin({ statuses: [0, 200] })],
  }),
);
registerRoute(navigationRoute);

// ── Tier 3: Background sync queues ────────────────────────────────────────────

// Outbox send: POST /api/v1/drafts/:id/send
// Replayed via workbox-background-sync when the device comes back online.
const outboxSyncPlugin = new BackgroundSyncPlugin("psense-mail-outbox", {
  maxRetentionTime: 24 * 60, // 24 hours in minutes
});

registerRoute(
  ({ url, request }) =>
    request.method === "POST" &&
    url.pathname.match(/\/api\/v1\/drafts\/[^/]+\/send$/) !== null,
  new NetworkFirst({
    cacheName: "psense-outbox-temp",
    plugins: [outboxSyncPlugin],
    networkTimeoutSeconds: 20,
  }),
  "POST",
);

// Bulk message actions: POST /api/v1/messages/actions
const actionSyncPlugin = new BackgroundSyncPlugin("psense-mail-actions", {
  maxRetentionTime: 24 * 60,
});

registerRoute(
  ({ url, request }) =>
    request.method === "POST" && url.pathname === "/api/v1/messages/actions",
  new NetworkFirst({
    cacheName: "psense-actions-temp",
    plugins: [actionSyncPlugin],
    networkTimeoutSeconds: 20,
  }),
  "POST",
);

// ── Tier 4: Push notifications (scaffold) ────────────────────────────────────

self.addEventListener("push", (event: PushEvent) => {
  if (!event.data) return;

  let payload: { title?: string; body?: string; url?: string; tag?: string } = {};
  try {
    payload = event.data.json() as typeof payload;
  } catch {
    payload = { title: "PSense Mail", body: event.data.text() };
  }

  const title = payload.title ?? "PSense Mail";
  const options: NotificationOptions = {
    body: payload.body ?? "You have a new message",
    icon: "/icons/icon-192.png",
    badge: "/icons/badge-72.png",
    tag: payload.tag ?? "psense-mail-notification",
    data: { url: payload.url ?? "/" },
    requireInteraction: false,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event: NotificationEvent) => {
  event.notification.close();

  const url = (event.notification.data as { url?: string })?.url ?? "/";

  event.waitUntil(
    (async () => {
      // Focus existing tab or open new one
      const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const client of clients) {
        if (client.url === url && "focus" in client) {
          await client.focus();
          return;
        }
      }
      await self.clients.openWindow(url);
    })(),
  );
});

// ── Sync event handler (Background Sync API) ─────────────────────────────────

// The BackgroundSyncPlugin above handles replay automatically via workbox.
// This handler is a hook for any additional sync work (e.g., triggering delta sync).
self.addEventListener("sync", (event: SyncEvent) => {
  if (event.tag === "psense-delta-sync") {
    // Notify all clients to run delta sync
    event.waitUntil(
      self.clients.matchAll({ type: "window" }).then((clients) => {
        for (const client of clients) {
          client.postMessage({ type: "DELTA_SYNC_REQUESTED" });
        }
      }),
    );
  }
});
