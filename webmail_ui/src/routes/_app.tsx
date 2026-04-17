import { Outlet, createFileRoute } from "@tanstack/react-router";
import { AppRail } from "@/components/layout/app-rail";
import { AppHeader } from "@/components/layout/app-header";
import { PoweredByFooter } from "@/components/powered-by-footer";

export const Route = createFileRoute("/_app")({
  ssr: false,
  component: AppLayout,
});

function AppLayout() {
  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-background text-foreground">
      <AppHeader />
      <div className="flex flex-1 overflow-hidden">
        <AppRail />
        <main className="flex flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
      <PoweredByFooter />
    </div>
  );
}
