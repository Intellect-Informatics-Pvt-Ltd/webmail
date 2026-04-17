export type EventCategory = "work" | "personal" | "focus" | "external" | "ooo";

export interface CalendarEvent {
  id: string;
  title: string;
  startISO: string;
  endISO: string;
  allDay?: boolean;
  location?: string;
  attendees?: { name: string; email: string }[];
  description?: string;
  category: EventCategory;
  isOrganizer?: boolean;
}

export const EVENT_CATEGORY_STYLES: Record<
  EventCategory,
  { dot: string; bg: string; ring: string; label: string }
> = {
  work: {
    label: "Work",
    dot: "bg-primary",
    bg: "bg-primary/10 text-primary border-primary/30",
    ring: "ring-primary/40",
  },
  personal: {
    label: "Personal",
    dot: "bg-success",
    bg: "bg-success/10 text-success-foreground border-success/30",
    ring: "ring-success/40",
  },
  focus: {
    label: "Focus",
    dot: "bg-info",
    bg: "bg-info/10 text-info-foreground border-info/30",
    ring: "ring-info/40",
  },
  external: {
    label: "External",
    dot: "bg-warning",
    bg: "bg-warning/10 text-warning-foreground border-warning/30",
    ring: "ring-warning/40",
  },
  ooo: {
    label: "Out of office",
    dot: "bg-destructive",
    bg: "bg-destructive/10 text-destructive border-destructive/30",
    ring: "ring-destructive/40",
  },
};

// Generate a realistic week of mock events around "today"
function buildSeed(): CalendarEvent[] {
  const now = new Date();
  const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  function at(dayOffset: number, hour: number, minute = 0) {
    const d = new Date(startOfDay);
    d.setDate(d.getDate() + dayOffset);
    d.setHours(hour, minute, 0, 0);
    return d.toISOString();
  }

  const me = { name: "Avery Chen", email: "avery@psense.ai" };
  const priya = { name: "Priya Raman", email: "priya@psense.ai" };
  const maya = { name: "Maya Sullivan", email: "maya@psense.ai" };
  const jordan = { name: "Jordan Patel", email: "jordan@northwind.co" };

  const events: CalendarEvent[] = [
    // ── Today
    {
      id: "ev-1",
      title: "Morning standup",
      startISO: at(0, 9, 0),
      endISO: at(0, 9, 15),
      category: "work",
      attendees: [me, priya, maya],
      location: "Zoom",
      isOrganizer: true,
    },
    {
      id: "ev-2",
      title: "Q1 board deck — final review",
      startISO: at(0, 10, 30),
      endISO: at(0, 11, 30),
      category: "work",
      attendees: [me, priya],
      description: "Walk through slides 12–18 before tomorrow's lock.",
      location: "Conference room A",
    },
    {
      id: "ev-3",
      title: "Focus block — write OKR draft",
      startISO: at(0, 13, 0),
      endISO: at(0, 15, 0),
      category: "focus",
    },
    {
      id: "ev-4",
      title: "Northwind discovery call",
      startISO: at(0, 15, 30),
      endISO: at(0, 16, 30),
      category: "external",
      attendees: [me, jordan],
      location: "Google Meet",
    },
    // ── Tomorrow
    {
      id: "ev-5",
      title: "1:1 with Priya",
      startISO: at(1, 9, 30),
      endISO: at(1, 10, 0),
      category: "work",
      attendees: [me, priya],
    },
    {
      id: "ev-6",
      title: "Design review — Mail v2",
      startISO: at(1, 11, 0),
      endISO: at(1, 12, 0),
      category: "work",
      attendees: [me, maya, priya],
    },
    {
      id: "ev-7",
      title: "Lunch with Sam",
      startISO: at(1, 12, 30),
      endISO: at(1, 13, 30),
      category: "personal",
      location: "Cafe Nero",
    },
    // ── In 2 days
    {
      id: "ev-8",
      title: "Customer advisory board",
      startISO: at(2, 14, 0),
      endISO: at(2, 16, 0),
      category: "external",
      attendees: [me, jordan, priya],
    },
    // ── In 3 days
    {
      id: "ev-9",
      title: "Engineering sync",
      startISO: at(3, 10, 0),
      endISO: at(3, 11, 0),
      category: "work",
    },
    {
      id: "ev-10",
      title: "Out of office",
      startISO: at(3, 0, 0),
      endISO: at(3, 23, 59),
      allDay: true,
      category: "ooo",
    },
    // ── In 4 days
    {
      id: "ev-11",
      title: "Quarterly planning offsite",
      startISO: at(4, 9, 0),
      endISO: at(4, 17, 0),
      category: "work",
      attendees: [me, priya, maya],
      location: "WeWork — Floor 3",
    },
    // ── Yesterday & earlier this week
    {
      id: "ev-12",
      title: "Design crit",
      startISO: at(-1, 14, 0),
      endISO: at(-1, 15, 0),
      category: "work",
    },
    {
      id: "ev-13",
      title: "Yoga",
      startISO: at(-2, 7, 0),
      endISO: at(-2, 8, 0),
      category: "personal",
    },
    // ── Spread across the month for month view density
    {
      id: "ev-14",
      title: "All-hands",
      startISO: at(7, 16, 0),
      endISO: at(7, 17, 0),
      category: "work",
    },
    {
      id: "ev-15",
      title: "Dentist",
      startISO: at(10, 11, 0),
      endISO: at(10, 12, 0),
      category: "personal",
    },
    {
      id: "ev-16",
      title: "Customer QBR — Acme",
      startISO: at(-5, 13, 0),
      endISO: at(-5, 14, 0),
      category: "external",
    },
    {
      id: "ev-17",
      title: "Roadmap review",
      startISO: at(-7, 10, 0),
      endISO: at(-7, 11, 30),
      category: "work",
    },
  ];

  return events;
}

export const CALENDAR_EVENTS: CalendarEvent[] = buildSeed();
