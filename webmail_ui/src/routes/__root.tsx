import { Outlet, Link, createRootRoute, HeadContent, Scripts, ClientOnly } from "@tanstack/react-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";

import appCss from "../styles.css?url";
import { ThemeManager } from "@/components/theme-manager";
import { GlobalOverlays } from "@/components/global-overlays";
import { ComposeWindow } from "@/components/compose/compose-window";
import { Toaster } from "@/components/ui/sonner";
import { ShortcutProvider } from "@/lib/shortcuts/provider";
import { QueryContextProvider } from "@/lib/query/context";
import { getBrowserQueryClient } from "@/lib/query/client";
import { usePWAUpdate } from "@/lib/pwa/use-pwa-update";
import { attachDeltaSync } from "@/lib/sync/delta";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "PSense Mail" },
      { name: "description", content: "PSense Mail — Enterprise workspace" },
      { name: "author", content: "PSense.ai" },
      { property: "og:title", content: "PSense Mail" },
      { property: "og:description", content: "PSense Mail — Enterprise workspace" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const queryClient = getBrowserQueryClient();
  const { needsRefresh, isOfflineReady, updateSW } = usePWAUpdate((data) => {
    // SW posted DELTA_SYNC_REQUESTED — trigger a sync cycle
    if ((data as { type?: string })?.type === "DELTA_SYNC_REQUESTED") {
      void queryClient.invalidateQueries();
    }
  });

  // Show toasts for PWA lifecycle events
  useEffect(() => {
    if (isOfflineReady) {
      toast.success("PSense Mail is ready to work offline.");
    }
  }, [isOfflineReady]);

  useEffect(() => {
    if (needsRefresh) {
      toast("Update available", {
        description: "A new version of PSense Mail is ready.",
        action: { label: "Reload", onClick: () => void updateSW(true) },
        duration: Infinity,
      });
    }
  }, [needsRefresh, updateSW]);

  // Attach delta sync once the client mounts.
  useEffect(() => {
    const ctx = { tenantId: "default", accountId: "default" };
    const detach = attachDeltaSync("default", ctx, queryClient, 30_000);
    return detach;
  }, [queryClient]);

  return (
    <QueryClientProvider client={queryClient}>
      <QueryContextProvider tenantId="default" accountId="default">
        <ShortcutProvider>
          <ThemeManager />
          <Outlet />
          <ClientOnly fallback={null}>
            <GlobalOverlays />
            <ComposeWindow />
          </ClientOnly>
          <Toaster />
        </ShortcutProvider>
      </QueryContextProvider>
    </QueryClientProvider>
  );
}
