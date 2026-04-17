import { Outlet, createFileRoute, useLocation, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { CalendarHeader } from "@/components/calendar/calendar-header";
import { CalendarSidebar } from "@/components/calendar/calendar-sidebar";
import { NewEventDialog } from "@/components/calendar/new-event-dialog";
import { useCalendarStore } from "@/stores/calendar-store";

export const Route = createFileRoute("/_app/calendar")({
  component: CalendarLayout,
});

function CalendarLayout() {
  const [newOpen, setNewOpen] = useState(false);
  const [prefill, setPrefill] = useState<{ start: Date; end: Date } | null>(null);
  const setView = useCalendarStore((s) => s.setView);
  const { pathname } = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (pathname === "/calendar") {
      navigate({ to: "/calendar/week", replace: true });
      return;
    }
    if (pathname.endsWith("/day")) setView("day");
    else if (pathname.endsWith("/week")) setView("week");
    else if (pathname.endsWith("/month")) setView("month");
  }, [pathname, navigate, setView]);

  // Listen for drag-to-create requests dispatched from the grid
  useEffect(() => {
    const h = (e: Event) => {
      const ce = e as CustomEvent<{ start: string; end: string }>;
      if (!ce.detail) return;
      setPrefill({ start: new Date(ce.detail.start), end: new Date(ce.detail.end) });
      setNewOpen(true);
    };
    window.addEventListener("calendar:create-range", h);
    return () => window.removeEventListener("calendar:create-range", h);
  }, []);

  return (
    <div className="flex h-full w-full flex-1 flex-col overflow-hidden bg-background">
      <CalendarHeader
        onCreate={() => {
          setPrefill(null);
          setNewOpen(true);
        }}
      />
      <div className="flex flex-1 overflow-hidden">
        <CalendarSidebar />
        <div className="flex-1 overflow-hidden">
          <Outlet />
        </div>
      </div>
      <NewEventDialog
        open={newOpen}
        onOpenChange={(v) => {
          setNewOpen(v);
          if (!v) setPrefill(null);
        }}
        prefillStart={prefill?.start}
        prefillEnd={prefill?.end}
      />
    </div>
  );
}
