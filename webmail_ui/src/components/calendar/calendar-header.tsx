import { Link, useLocation } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  CalendarDays,
} from "lucide-react";
import { useCalendarStore, type CalendarView } from "@/stores/calendar-store";
import {
  formatDayLabel,
  formatMonthLabel,
  formatWeekRange,
  startOfWeek,
} from "@/lib/calendar-utils";
import { cn } from "@/lib/utils";

const VIEWS: { id: CalendarView; label: string; to: "/calendar/day" | "/calendar/week" | "/calendar/month" }[] = [
  { id: "day", label: "Day", to: "/calendar/day" },
  { id: "week", label: "Week", to: "/calendar/week" },
  { id: "month", label: "Month", to: "/calendar/month" },
];

export function CalendarHeader({ onCreate }: { onCreate: () => void }) {
  const view = useCalendarStore((s) => s.view);
  const cursorISO = useCalendarStore((s) => s.cursorISO);
  const step = useCalendarStore((s) => s.step);
  const goToday = useCalendarStore((s) => s.goToday);
  const { pathname } = useLocation();

  const cursor = new Date(cursorISO);
  let label: string;
  if (view === "day") label = formatDayLabel(cursor);
  else if (view === "week") label = formatWeekRange(startOfWeek(cursor));
  else label = formatMonthLabel(cursor);

  return (
    <header className="flex flex-wrap items-center gap-2 border-b border-border bg-background px-4 py-3">
      <div className="flex items-center gap-2">
        <CalendarDays className="h-5 w-5 text-primary" aria-hidden />
        <h1 className="text-lg font-semibold tracking-tight">Calendar</h1>
      </div>

      <div className="ml-2 flex items-center gap-1">
        <Button variant="outline" size="sm" onClick={goToday}>
          Today
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Previous"
          onClick={() => step(-1)}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Next"
          onClick={() => step(1)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="ml-2 text-sm font-medium">{label}</div>

      <div className="ml-auto flex items-center gap-2">
        <div className="inline-flex rounded-md border border-border p-0.5">
          {VIEWS.map((v) => {
            const active = pathname === v.to;
            return (
              <Link
                key={v.id}
                to={v.to}
                className={cn(
                  "rounded-sm px-3 py-1 text-xs font-medium transition-colors",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted",
                )}
              >
                {v.label}
              </Link>
            );
          })}
        </div>
        <Button size="sm" onClick={onCreate} className="gap-1.5">
          <Plus className="h-4 w-4" /> Event
        </Button>
      </div>
    </header>
  );
}
