import { createFileRoute } from "@tanstack/react-router";
import { CalendarGrid } from "@/components/calendar/calendar-grid";

export const Route = createFileRoute("/_app/calendar/week")({
  component: () => <CalendarGrid mode="week" />,
});
