import { createFileRoute } from "@tanstack/react-router";
import { CalendarMonth } from "@/components/calendar/calendar-month";

export const Route = createFileRoute("/_app/calendar/month")({
  component: CalendarMonth,
});
