import { useMemo } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCalendarStore } from "@/stores/calendar-store";
import {
  addDays,
  isSameDay,
  isSameMonth,
  startOfMonth,
  startOfWeek,
} from "@/lib/calendar-utils";
import {
  EVENT_CATEGORY_STYLES,
  type EventCategory,
} from "@/data/calendar-events";
import { cn } from "@/lib/utils";

const WEEKDAY_INITIALS = ["M", "T", "W", "T", "F", "S", "S"];
const ALL_CATEGORIES: EventCategory[] = [
  "work",
  "personal",
  "focus",
  "external",
  "ooo",
];

export function CalendarSidebar() {
  const cursorISO = useCalendarStore((s) => s.cursorISO);
  const setCursor = useCalendarStore((s) => s.setCursor);
  const setView = useCalendarStore((s) => s.setView);
  const events = useCalendarStore((s) => s.events);
  const hidden = useCalendarStore((s) => s.hiddenCategories);
  const toggleCategory = useCalendarStore((s) => s.toggleCategory);

  const cursor = new Date(cursorISO);
  const today = new Date();

  const monthStart = startOfMonth(cursor);
  const gridStart = startOfWeek(monthStart);
  const cells = useMemo(
    () => Array.from({ length: 42 }, (_, i) => addDays(gridStart, i)),
    [gridStart],
  );

  // Days with at least one event (not hidden) → show a dot marker
  const eventDays = useMemo(() => {
    const set = new Set<string>();
    for (const ev of events) {
      if (hidden.includes(ev.category)) continue;
      const d = new Date(ev.startISO);
      const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
      set.add(key);
    }
    return set;
  }, [events, hidden]);

  function shiftMonth(dir: -1 | 1) {
    const d = new Date(cursor);
    d.setDate(1);
    d.setMonth(d.getMonth() + dir);
    setCursor(d.toISOString());
  }

  return (
    <aside className="hidden w-60 shrink-0 flex-col gap-5 border-r border-border bg-background/50 p-3 lg:flex">
      {/* Mini month */}
      <section>
        <header className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-tight">
            {cursor.toLocaleDateString(undefined, {
              month: "long",
              year: "numeric",
            })}
          </h2>
          <div className="flex items-center gap-0.5">
            <button
              type="button"
              onClick={() => shiftMonth(-1)}
              className="inline-flex h-6 w-6 items-center justify-center rounded hover:bg-muted"
              aria-label="Previous month"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => shiftMonth(1)}
              className="inline-flex h-6 w-6 items-center justify-center rounded hover:bg-muted"
              aria-label="Next month"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </header>
        <div className="grid grid-cols-7 gap-y-0.5 text-center">
          {WEEKDAY_INITIALS.map((d, i) => (
            <div
              key={`${d}-${i}`}
              className="text-[10px] font-semibold uppercase text-muted-foreground"
            >
              {d}
            </div>
          ))}
          {cells.map((day) => {
            const inMonth = isSameMonth(day, cursor);
            const isToday = isSameDay(day, today);
            const isSelected = isSameDay(day, cursor);
            const key = `${day.getFullYear()}-${day.getMonth()}-${day.getDate()}`;
            const hasEvents = eventDays.has(key);
            return (
              <button
                key={day.toISOString()}
                type="button"
                onClick={() => {
                  setCursor(day.toISOString());
                  setView("day");
                }}
                className={cn(
                  "relative mx-auto inline-flex h-7 w-7 items-center justify-center rounded-full text-[11px] transition-colors",
                  !inMonth && "text-muted-foreground/40",
                  inMonth && !isToday && !isSelected && "hover:bg-muted",
                  isSelected && !isToday && "bg-primary/15 font-semibold text-primary",
                  isToday && "bg-primary font-semibold text-primary-foreground",
                )}
                aria-label={day.toDateString()}
              >
                {day.getDate()}
                {hasEvents && !isToday && (
                  <span
                    className={cn(
                      "absolute bottom-0.5 h-1 w-1 rounded-full",
                      isSelected ? "bg-primary" : "bg-muted-foreground/60",
                    )}
                    aria-hidden
                  />
                )}
              </button>
            );
          })}
        </div>
      </section>

      {/* My calendars */}
      <section>
        <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          My calendars
        </h2>
        <ul className="space-y-0.5">
          {ALL_CATEGORIES.map((cat) => {
            const style = EVENT_CATEGORY_STYLES[cat];
            const isHidden = hidden.includes(cat);
            return (
              <li key={cat}>
                <button
                  type="button"
                  onClick={() => toggleCategory(cat)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted",
                    isHidden && "text-muted-foreground",
                  )}
                  aria-pressed={!isHidden}
                >
                  <span
                    className={cn(
                      "h-3 w-3 shrink-0 rounded-sm border",
                      isHidden
                        ? "border-border bg-transparent"
                        : `border-transparent ${style.dot}`,
                    )}
                    aria-hidden
                  />
                  <span className={cn("truncate", isHidden && "line-through")}>
                    {style.label}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>
    </aside>
  );
}
