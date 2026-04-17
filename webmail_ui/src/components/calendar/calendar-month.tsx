import { useMemo, useState } from "react";
import { useCalendarStore } from "@/stores/calendar-store";
import {
  addDays,
  eventsOnDay,
  isSameDay,
  isSameMonth,
  startOfMonth,
  startOfWeek,
} from "@/lib/calendar-utils";
import { EVENT_CATEGORY_STYLES, type CalendarEvent } from "@/data/calendar-events";
import { cn } from "@/lib/utils";
import { EventDrawer } from "./event-drawer";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function CalendarMonth() {
  const events = useCalendarStore((s) => s.events);
  const hidden = useCalendarStore((s) => s.hiddenCategories);
  const cursorISO = useCalendarStore((s) => s.cursorISO);
  const setCursor = useCalendarStore((s) => s.setCursor);
  const setView = useCalendarStore((s) => s.setView);
  const [selected, setSelected] = useState<CalendarEvent | null>(null);

  const cursor = new Date(cursorISO);
  const monthStart = startOfMonth(cursor);
  const gridStart = startOfWeek(monthStart);

  const cells = useMemo(
    () => Array.from({ length: 42 }, (_, i) => addDays(gridStart, i)),
    [gridStart],
  );

  const visibleEvents = useMemo(
    () => events.filter((e) => !hidden.includes(e.category)),
    [events, hidden],
  );

  const today = new Date();

  return (
    <>
      <div className="flex h-full flex-col">
        <div className="grid grid-cols-7 border-b border-border bg-muted/30">
          {WEEKDAYS.map((d) => (
            <div
              key={d}
              className="px-2 py-2 text-center text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
            >
              {d}
            </div>
          ))}
        </div>

        <div className="grid flex-1 grid-cols-7 grid-rows-6">
          {cells.map((day) => {
            const inMonth = isSameMonth(day, cursor);
            const isToday = isSameDay(day, today);
            const dayEvents = eventsOnDay(visibleEvents, day);
            const visible = dayEvents.slice(0, 3);
            const overflow = dayEvents.length - visible.length;

            return (
              <div
                key={day.toISOString()}
                className={cn(
                  "min-h-[88px] border-b border-r border-border p-1.5 text-left",
                  !inMonth && "bg-muted/20 text-muted-foreground",
                )}
              >
                <button
                  type="button"
                  onClick={() => {
                    setCursor(day.toISOString());
                    setView("day");
                  }}
                  className={cn(
                    "mb-1 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold transition-colors hover:bg-primary/10",
                    isToday && "bg-primary text-primary-foreground hover:bg-primary",
                  )}
                  aria-label={`Open ${day.toDateString()}`}
                >
                  {day.getDate()}
                </button>
                <div className="space-y-0.5">
                  {visible.map((ev) => {
                    const style = EVENT_CATEGORY_STYLES[ev.category];
                    return (
                      <button
                        key={ev.id}
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelected(ev);
                        }}
                        className={cn(
                          "flex w-full items-center gap-1 truncate rounded px-1 py-0.5 text-left text-[11px] hover:bg-muted",
                        )}
                      >
                        <span
                          className={cn("h-1.5 w-1.5 shrink-0 rounded-full", style.dot)}
                          aria-hidden
                        />
                        <span className="truncate font-medium">{ev.title}</span>
                      </button>
                    );
                  })}
                  {overflow > 0 && (
                    <div className="px-1 text-[10px] text-muted-foreground">
                      +{overflow} more
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <EventDrawer
        event={selected}
        open={!!selected}
        onOpenChange={(o) => !o && setSelected(null)}
      />
    </>
  );
}
