import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCalendarStore } from "@/stores/calendar-store";
import type { CalendarEvent, EventCategory } from "@/data/calendar-events";
import { toast } from "sonner";

function toDateInput(d: Date) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function toTimeInput(d: Date) {
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function NewEventDialog({
  open,
  onOpenChange,
  defaultDate,
  prefillStart,
  prefillEnd,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  defaultDate?: Date;
  prefillStart?: Date;
  prefillEnd?: Date;
}) {
  const addEvent = useCalendarStore((s) => s.addEvent);

  const [title, setTitle] = useState("");
  const [date, setDate] = useState(toDateInput(defaultDate ?? new Date()));
  const [start, setStart] = useState("10:00");
  const [end, setEnd] = useState("11:00");
  const [category, setCategory] = useState<EventCategory>("work");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");

  // When the dialog opens, sync prefill values (or reset)
  useEffect(() => {
    if (!open) return;
    if (prefillStart && prefillEnd) {
      setDate(toDateInput(prefillStart));
      setStart(toTimeInput(prefillStart));
      setEnd(toTimeInput(prefillEnd));
    } else if (defaultDate) {
      setDate(toDateInput(defaultDate));
    } else {
      setDate(toDateInput(new Date()));
    }
  }, [open, prefillStart, prefillEnd, defaultDate]);

  function reset() {
    setTitle("");
    setStart("10:00");
    setEnd("11:00");
    setCategory("work");
    setLocation("");
    setDescription("");
  }

  function save() {
    if (!title.trim()) {
      toast.error("Add a title");
      return;
    }
    const startISO = new Date(`${date}T${start}:00`).toISOString();
    const endISO = new Date(`${date}T${end}:00`).toISOString();
    if (new Date(endISO) <= new Date(startISO)) {
      toast.error("End time must be after start");
      return;
    }
    const event: CalendarEvent = {
      id: `ev-${Date.now()}`,
      title: title.trim(),
      startISO,
      endISO,
      category,
      location: location.trim() || undefined,
      description: description.trim() || undefined,
      isOrganizer: true,
    };
    addEvent(event);
    toast.success("Event created");
    reset();
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New event</DialogTitle>
          <DialogDescription>
            Block time on your calendar. Mock data only — won't sync to a real calendar yet.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="ev-title">Title</Label>
            <Input
              id="ev-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Sync with Priya"
              autoFocus
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="ev-date">Date</Label>
              <Input
                id="ev-date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ev-start">Start</Label>
              <Input
                id="ev-start"
                type="time"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ev-end">End</Label>
              <Input
                id="ev-end"
                type="time"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label>Category</Label>
              <Select value={category} onValueChange={(v) => setCategory(v as EventCategory)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="work">Work</SelectItem>
                  <SelectItem value="personal">Personal</SelectItem>
                  <SelectItem value="focus">Focus</SelectItem>
                  <SelectItem value="external">External</SelectItem>
                  <SelectItem value="ooo">Out of office</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ev-loc">Location</Label>
              <Input
                id="ev-loc"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Zoom, Room A, ..."
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ev-desc">Description</Label>
            <Textarea
              id="ev-desc"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Notes, agenda, links..."
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save}>Create event</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
