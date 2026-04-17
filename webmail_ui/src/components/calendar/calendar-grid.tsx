import { useMemo, useRef, useState } from "react";
import { useCalendarStore } from "@/stores/calendar-store";
import {
  HOURS,
  addDays,
  eventsOnDay,
  formatTime,
  isSameDay,
  pixelsPerHour,
  startOfDay,
  startOfWeek,
} from "@/lib/calendar-utils";
import { EVENT_CATEGORY_STYLES, type CalendarEvent } from "@/data/calendar-events";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EventDrawer } from "./event-drawer";

interface CalendarGridProps {
  mode: "day" | "week";
}

interface DragState {
  dayKey: string;
  day: Date;
  startMin: number;
  endMin: number;
}

const SNAP_MIN = 15;

export function CalendarGrid({ mode }: CalendarGridProps) {
  const events = useCalendarStore((s) => s.events);
  const cursorISO = useCalendarStore((s) => s.cursorISO);
  const hidden = useCalendarStore((s) => s.hiddenCategories);
  const [selected, setSelected] = useState<CalendarEvent | null>(null);
  const [drag, setDrag] = useState<DragState | null>(null);
  const dragRef = useRef<DragState | null>(null);

  const days = useMemo(() => {
    const cursor = new Date(cursorISO);
    if (mode === "day") return [startOfDay(cursor)];
    const weekStart = startOfWeek(cursor);
    return Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  }, [cursorISO, mode]);

  const visibleEvents = useMemo(
    () => events.filter((e) => !hidden.includes(e.category)),
    [events, hidden],
  );

  const hourPx = pixelsPerHour();
  const today = new Date();

  function minutesFromY(e: React.MouseEvent, target: HTMLElement) {
    const rect = target.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const raw = (y / hourPx) * 60;
    return Math.max(0, Math.min(24 * 60, Math.round(raw / SNAP_MIN) * SNAP_MIN));
  }

  function handleMouseDown(e: React.MouseEvent<HTMLDivElement>, day: Date) {
    if (e.button !== 0) return;
    // Ignore if clicking an event button
    if ((e.target as HTMLElement).closest("button")) return;
    const grid = e.currentTarget;
    const min = minutesFromY(e, grid);
    const next: DragState = {
      dayKey: day.toISOString(),
      day,
      startMin: min,
      endMin: min + 30,
    };
    dragRef.current = next;
    setDrag(next);
    e.preventDefault();
  }

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    if (!dragRef.current) return;
    const min = minutesFromY(e, e.currentTarget);
    const next = {
      ...dragRef.current,
      endMin: Math.max(dragRef.current.startMin + SNAP_MIN, min),
    };
    dragRef.current = next;
    setDrag(next);
  }

  function commitDrag() {
    const d = dragRef.current;
    dragRef.current = null;
    setDrag(null);
    if (!d) return;
    if (d.endMin - d.startMin < SNAP_MIN) return;
    const start = new Date(d.day);
    start.setHours(0, 0, 0, 0);
    start.setMinutes(d.startMin);
    const end = new Date(d.day);
    end.setHours(0, 0, 0, 0);
    end.setMinutes(d.endMin);
    window.dispatchEvent(
      new CustomEvent("calendar:create-range", {
        detail: { start: start.toISOString(), end: end.toISOString() },
      }),
    );
  }

  return (
    <>
      <ScrollArea className="h-full w-full">
        <div className="flex">
          {/* Time gutter */}
          <div className="sticky left-0 z-10 w-14 shrink-0 border-r border-border bg-background">
            <div className="h-12 border-b border-border" />
            {HOURS.map((h) => (
              <div
                key={h}
                className="relative border-b border-border text-[10px] text-muted-foreground"
                style={{ height: hourPx }}
              >
                <span className="absolute -top-1.5 right-1.5">
                  {h === 0 ? "" : `${h % 12 || 12}${h < 12 ? "a" : "p"}`}
                </span>
              </div>
            ))}
          </div>

          {/* Day columns */}
          <div
            className="grid flex-1"
            style={{ gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))` }}
          >
            {days.map((day) => {
              const dayEvents = eventsOnDay(visibleEvents, day);
              const allDay = dayEvents.filter((e) => e.allDay);
              const timed = dayEvents.filter((e) => !e.allDay);
              const isToday = isSameDay(day, today);
              const dayKey = day.toISOString();
              const dragOnThis = drag && drag.dayKey === dayKey;

              return (
                <div
                  key={dayKey}
                  className="relative border-r border-border last:border-r-0"
                >
                  {/* Day header */}
                  <div
                    className={cn(
                      "sticky top-0 z-10 flex h-12 flex-col items-center justify-center border-b border-border bg-background",
                      isToday && "bg-primary/5",
                    )}
                  >
                    <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      {day.toLocaleDateString(undefined, { weekday: "short" })}
                    </div>
                    <div
                      className={cn(
                        "flex h-6 w-6 items-center justify-center rounded-full text-sm font-semibold",
                        isToday && "bg-primary text-primary-foreground",
                      )}
                    >
                      {day.getDate()}
                    </div>
                  </div>

                  {/* All-day strip */}
                  {allDay.length > 0 && (
                    <div className="space-y-1 border-b border-border bg-muted/30 p-1">
                      {allDay.map((ev) => {
                        const style = EVENT_CATEGORY_STYLES[ev.category];
                        return (
                          <button
                            key={ev.id}
                            type="button"
                            onClick={() => setSelected(ev)}
                            className={cn(
                              "block w-full truncate rounded border px-1.5 py-0.5 text-left text-[11px] font-medium",
                              style.bg,
                            )}
                          >
                            {ev.title}
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* Hour rows + drag-to-create surface */}
                  <div
                    className="relative cursor-crosshair select-none"
                    onMouseDown={(e) => handleMouseDown(e, day)}
                    onMouseMove={handleMouseMove}
                    onMouseUp={commitDrag}
                    onMouseLeave={() => {
                      if (dragRef.current) commitDrag();
                    }}
                  >
                    {HOURS.map((h) => (
                      <div
                        key={h}
                        className="border-b border-border"
                        style={{ height: hourPx }}
                      />
                    ))}

                    {/* Now line */}
                    {isToday && <NowLine hourPx={hourPx} />}

                    {/* Drag preview ghost */}
                    {dragOnThis && (
                      <div
                        className="pointer-events-none absolute left-1 right-1 rounded-md border-2 border-dashed border-primary bg-primary/10 px-2 py-1 text-[11px] font-medium text-primary"
                        style={{
                          top: (drag!.startMin / 60) * hourPx,
                          height: Math.max(
                            18,
                            ((drag!.endMin - drag!.startMin) / 60) * hourPx - 2,
                          ),
                        }}
                      >
                        {formatRangeLabel(drag!.startMin, drag!.endMin)}
                      </div>
                    )}

                    {/* Timed events */}
                    {timed.map((ev) => {
                      const start = new Date(ev.startISO);
                      const end = new Date(ev.endISO);
                      const dayStart = startOfDay(day);
                      const startMin = Math.max(
                        0,
                        (start.getTime() - dayStart.getTime()) / 60000,
                      );
                      const endMin = Math.min(
                        24 * 60,
                        (end.getTime() - dayStart.getTime()) / 60000,
                      );
                      const top = (startMin / 60) * hourPx;
                      const height = Math.max(20, ((endMin - startMin) / 60) * hourPx - 2);
                      const style = EVENT_CATEGORY_STYLES[ev.category];

                      return (
                        <button
                          key={ev.id}
                          type="button"
                          onMouseDown={(e) => e.stopPropagation()}
                          onClick={() => setSelected(ev)}
                          className={cn(
                            "absolute left-1 right-1 overflow-hidden rounded-md border px-2 py-1 text-left text-[11px] shadow-sm transition-shadow hover:shadow-md focus:outline-none focus:ring-2",
                            style.bg,
                            style.ring,
                          )}
                          style={{ top, height }}
                        >
                          <div className="truncate font-semibold">{ev.title}</div>
                          {height > 32 && (
                            <div className="truncate opacity-80">
                              {formatTime(start)} – {formatTime(end)}
                            </div>
                          )}
                          {height > 56 && ev.location && (
                            <div className="mt-0.5 truncate text-[10px] opacity-70">
                              {ev.location}
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </ScrollArea>

      <EventDrawer
        event={selected}
        open={!!selected}
        onOpenChange={(o) => !o && setSelected(null)}
      />
    </>
  );
}

function formatRangeLabel(startMin: number, endMin: number) {
  const fmt = (m: number) => {
    const h = Math.floor(m / 60);
    const mm = m % 60;
    const ampm = h < 12 ? "a" : "p";
    const h12 = h % 12 || 12;
    return `${h12}:${String(mm).padStart(2, "0")}${ampm}`;
  };
  return `${fmt(startMin)} – ${fmt(endMin)}`;
}

function NowLine({ hourPx }: { hourPx: number }) {
  const now = new Date();
  const minutes = now.getHours() * 60 + now.getMinutes();
  const top = (minutes / 60) * hourPx;
  return (
    <div
      className="pointer-events-none absolute left-0 right-0 z-20 border-t-2 border-destructive"
      style={{ top }}
    >
      <span className="absolute -left-1 -top-1.5 h-3 w-3 rounded-full bg-destructive" />
    </div>
  );
}
