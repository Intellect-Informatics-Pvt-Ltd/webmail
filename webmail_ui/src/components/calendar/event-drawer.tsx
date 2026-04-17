import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { initialsOf } from "@/lib/mail-format";
import { formatTime, formatDayLabel } from "@/lib/calendar-utils";
import { EVENT_CATEGORY_STYLES, type CalendarEvent } from "@/data/calendar-events";
import { useCalendarStore } from "@/stores/calendar-store";
import { useComposeStore } from "@/stores/compose-store";
import { Trash2, MapPin, Users, Clock, Mail } from "lucide-react";
import { toast } from "sonner";

export function EventDrawer({
  event,
  open,
  onOpenChange,
}: {
  event: CalendarEvent | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const deleteEvent = useCalendarStore((s) => s.deleteEvent);
  const openCompose = useComposeStore((s) => s.openCompose);

  if (!event) return null;
  const style = EVENT_CATEGORY_STYLES[event.category];
  const start = new Date(event.startISO);
  const end = new Date(event.endISO);

  const emailAttendees = () => {
    if (!event?.attendees?.length) return;
    openCompose({
      to: event.attendees,
      subject: `Re: ${event.title}`,
      bodyHtml: `<p>Hi all,</p><p></p>`,
    });
    onOpenChange(false);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader className="space-y-3">
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${style.dot}`} aria-hidden />
            <Badge variant="outline" className="text-xs">
              {style.label}
            </Badge>
            {event.isOrganizer && (
              <Badge variant="secondary" className="text-xs">
                Organizer
              </Badge>
            )}
          </div>
          <SheetTitle className="text-left text-xl">{event.title}</SheetTitle>
          <SheetDescription className="text-left">
            <span className="flex items-center gap-2 text-sm">
              <Clock className="h-4 w-4" />
              {formatDayLabel(start)} ·{" "}
              {event.allDay ? (
                "All day"
              ) : (
                <>
                  {formatTime(start)} – {formatTime(end)}
                </>
              )}
            </span>
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-5">
          {event.location && (
            <Section icon={<MapPin className="h-4 w-4" />} label="Location">
              <p className="text-sm">{event.location}</p>
            </Section>
          )}

          {event.attendees?.length ? (
            <Section icon={<Users className="h-4 w-4" />} label={`Attendees (${event.attendees.length})`}>
              <ul className="space-y-2">
                {event.attendees.map((a) => (
                  <li key={a.email} className="flex items-center gap-2.5">
                    <Avatar className="h-7 w-7">
                      <AvatarFallback className="bg-primary/10 text-xs text-primary">
                        {initialsOf(a.name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">{a.name}</div>
                      <div className="truncate text-xs text-muted-foreground">
                        {a.email}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {event.description && (
            <Section icon={<Mail className="h-4 w-4" />} label="Description">
              <p className="whitespace-pre-line text-sm text-foreground/80">
                {event.description}
              </p>
            </Section>
          )}
        </div>

        <SheetFooter className="mt-8 flex-row gap-2">
          {event.attendees?.length ? (
            <Button variant="outline" className="flex-1" onClick={emailAttendees}>
              <Mail className="mr-2 h-4 w-4" /> Email attendees
            </Button>
          ) : null}
          <Button
            variant="ghost"
            className="text-muted-foreground hover:text-destructive"
            onClick={() => {
              deleteEvent(event.id);
              toast(`Deleted "${event.title}"`);
              onOpenChange(false);
            }}
            aria-label="Delete"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

function Section({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {icon}
        {label}
      </div>
      {children}
    </div>
  );
}
