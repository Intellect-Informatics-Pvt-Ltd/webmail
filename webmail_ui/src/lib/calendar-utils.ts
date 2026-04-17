// Calendar date helpers — pure, ISO-string in/out
export function startOfDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

export function startOfWeek(d: Date): Date {
  const x = startOfDay(d);
  // Week starts on Monday
  const day = x.getDay(); // 0 = Sun
  const diff = (day + 6) % 7;
  x.setDate(x.getDate() - diff);
  return x;
}

export function startOfMonth(d: Date): Date {
  const x = startOfDay(d);
  x.setDate(1);
  return x;
}

export function addDays(d: Date, n: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}

export function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function isSameMonth(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();
}

export function formatDayLabel(d: Date): string {
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function formatMonthLabel(d: Date): string {
  return d.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

export function formatWeekRange(start: Date): string {
  const end = addDays(start, 6);
  const sameMonth = start.getMonth() === end.getMonth();
  const sameYear = start.getFullYear() === end.getFullYear();
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  const startStr = start.toLocaleDateString(undefined, opts);
  const endStr = end.toLocaleDateString(undefined, sameMonth ? { day: "numeric" } : opts);
  const yearStr = sameYear ? start.getFullYear() : `${start.getFullYear()}–${end.getFullYear()}`;
  return `${startStr} – ${endStr}, ${yearStr}`;
}

export function formatTime(d: Date): string {
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function eventsOnDay<T extends { startISO: string; endISO: string; allDay?: boolean }>(
  events: T[],
  day: Date,
): T[] {
  return events
    .filter((e) => {
      const s = new Date(e.startISO);
      const eend = new Date(e.endISO);
      // Event overlaps day if it starts before end-of-day and ends after start-of-day
      const dayStart = startOfDay(day);
      const dayEnd = addDays(dayStart, 1);
      return s < dayEnd && eend > dayStart;
    })
    .sort((a, b) => +new Date(a.startISO) - +new Date(b.startISO));
}

export const HOURS = Array.from({ length: 24 }, (_, i) => i);

export function pixelsPerHour(): number {
  return 56;
}
