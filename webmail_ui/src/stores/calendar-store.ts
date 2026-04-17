import { create } from "zustand";
import { persist } from "zustand/middleware";
import { CALENDAR_EVENTS, type CalendarEvent, type EventCategory } from "@/data/calendar-events";

export type CalendarView = "day" | "week" | "month";

interface CalendarState {
  events: CalendarEvent[];
  view: CalendarView;
  cursorISO: string; // anchor date for current view
  hiddenCategories: EventCategory[]; // categories to hide
  setView: (v: CalendarView) => void;
  setCursor: (iso: string) => void;
  goToday: () => void;
  step: (direction: -1 | 1) => void;
  addEvent: (event: CalendarEvent) => void;
  updateEvent: (event: CalendarEvent) => void;
  deleteEvent: (id: string) => void;
  toggleCategory: (category: EventCategory) => void;
}

function startOfToday() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

export const useCalendarStore = create<CalendarState>()(
  persist(
    (set, get) => ({
      events: CALENDAR_EVENTS,
      view: "week",
      cursorISO: startOfToday(),
      hiddenCategories: [],
      setView: (view) => set({ view }),
      setCursor: (iso) => set({ cursorISO: iso }),
      goToday: () => set({ cursorISO: startOfToday() }),
      step: (direction) => {
        const { view, cursorISO } = get();
        const d = new Date(cursorISO);
        if (view === "day") d.setDate(d.getDate() + direction);
        else if (view === "week") d.setDate(d.getDate() + 7 * direction);
        else {
          d.setDate(1);
          d.setMonth(d.getMonth() + direction);
        }
        set({ cursorISO: d.toISOString() });
      },
      addEvent: (event) => set((s) => ({ events: [event, ...s.events] })),
      updateEvent: (event) =>
        set((s) => ({
          events: s.events.map((e) => (e.id === event.id ? event : e)),
        })),
      deleteEvent: (id) => set((s) => ({ events: s.events.filter((e) => e.id !== id) })),
      toggleCategory: (category) =>
        set((s) => ({
          hiddenCategories: s.hiddenCategories.includes(category)
            ? s.hiddenCategories.filter((c) => c !== category)
            : [...s.hiddenCategories, category],
        })),
    }),
    { name: "psense-calendar", version: 2 },
  ),
);
