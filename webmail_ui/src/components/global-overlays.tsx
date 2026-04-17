import { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useUIStore } from "@/stores/ui-store";
import { useMailStore } from "@/stores/mail-store";
import { useComposeStore } from "@/stores/compose-store";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { CATEGORIES, CATEGORY_STYLES } from "@/data/categories";
import { cn } from "@/lib/utils";
import {
  Inbox,
  Send,
  Archive,
  Trash2,
  Flag,
  Settings,
  PenSquare,
  FileEdit,
  Folder,
  Wand2,
  FileText,
  Keyboard,
  Search,
} from "lucide-react";
import { toast } from "sonner";

const SHORTCUTS: { keys: string[]; desc: string }[] = [
  { keys: ["c"], desc: "Compose new message" },
  { keys: ["/"], desc: "Focus search" },
  { keys: ["⌘", "K"], desc: "Open command palette" },
  { keys: ["j"], desc: "Next message" },
  { keys: ["k"], desc: "Previous message" },
  { keys: ["e"], desc: "Archive" },
  { keys: ["#"], desc: "Delete" },
  { keys: ["u"], desc: "Toggle read/unread" },
  { keys: ["f"], desc: "Toggle flag" },
  { keys: ["?"], desc: "Show shortcuts" },
];

export function GlobalOverlays() {
  const shortcutsOpen = useUIStore((s) => s.shortcutsOpen);
  const openShortcuts = useUIStore((s) => s.openShortcuts);
  const paletteOpen = useUIStore((s) => s.paletteOpen);
  const openPalette = useUIStore((s) => s.openPalette);
  const newFolderOpen = useUIStore((s) => s.newFolderOpen);
  const openNewFolder = useUIStore((s) => s.openNewFolder);
  const moveToOpen = useUIStore((s) => s.moveToOpen);
  const openMoveTo = useUIStore((s) => s.openMoveTo);
  const snoozeOpen = useUIStore((s) => s.snoozeOpen);
  const openSnooze = useUIStore((s) => s.openSnooze);
  const categorizeOpen = useUIStore((s) => s.categorizeOpen);
  const openCategorize = useUIStore((s) => s.openCategorize);

  const selectedRowIds = useUIStore((s) => s.selectedRowIds);
  const selectedThreadId = useUIStore((s) => s.selectedThreadId);
  const clearSelection = useUIStore((s) => s.clearSelection);

  const customFolders = useMailStore((s) => s.customFolders);
  const folders = useMailStore((s) => s.folders);
  const messages = useMailStore((s) => s.messages);
  const addFolder = useMailStore((s) => s.addFolder);
  const moveTo = useMailStore((s) => s.moveTo);
  const snooze = useMailStore((s) => s.snooze);
  const categorize = useMailStore((s) => s.categorize);

  const openCompose = useComposeStore((s) => s.openCompose);
  const navigate = useNavigate();

  // global keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      const inField =
        t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        openPalette(true);
        return;
      }
      if (inField) return;
      if (e.key === "?") {
        e.preventDefault();
        openShortcuts(true);
      } else if (e.key === "c") {
        e.preventDefault();
        openCompose();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [openCompose, openPalette, openShortcuts]);

  // resolve target ids for overlays
  const targetIds =
    selectedRowIds.length > 0
      ? selectedRowIds
      : selectedThreadId
        ? messages.filter((m) => m.threadId === selectedThreadId).map((m) => m.id)
        : [];

  const [newFolderName, setNewFolderName] = useState("");
  const [snoozeDate, setSnoozeDate] = useState<Date | undefined>(
    new Date(Date.now() + 24 * 3600_000),
  );

  return (
    <>
      {/* Shortcuts modal */}
      <Dialog open={shortcutsOpen} onOpenChange={(v) => openShortcuts(v)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Keyboard className="h-4 w-4" /> Keyboard shortcuts
            </DialogTitle>
            <DialogDescription>
              Triage faster with these keys. Most work when the message list is focused.
            </DialogDescription>
          </DialogHeader>
          <ul className="divide-y divide-border">
            {SHORTCUTS.map((s) => (
              <li key={s.desc} className="flex items-center justify-between py-2 text-sm">
                <span>{s.desc}</span>
                <span className="flex items-center gap-1">
                  {s.keys.map((k, i) => (
                    <kbd
                      key={i}
                      className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[11px]"
                    >
                      {k}
                    </kbd>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        </DialogContent>
      </Dialog>

      {/* Command palette */}
      <Dialog open={paletteOpen} onOpenChange={(v) => openPalette(v)}>
        <DialogContent className="overflow-hidden p-0 sm:max-w-xl">
          <Command>
            <CommandInput placeholder="Type a command or search…" autoFocus />
            <CommandList>
              <CommandEmpty>No results.</CommandEmpty>
              <CommandGroup heading="Actions">
                <CommandItem
                  onSelect={() => {
                    openCompose();
                    openPalette(false);
                  }}
                >
                  <PenSquare className="mr-2 h-4 w-4" /> New message
                </CommandItem>
                <CommandItem
                  onSelect={() => {
                    openNewFolder(true);
                    openPalette(false);
                  }}
                >
                  <Folder className="mr-2 h-4 w-4" /> New folder
                </CommandItem>
                <CommandItem
                  onSelect={() => {
                    openShortcuts(true);
                    openPalette(false);
                  }}
                >
                  <Keyboard className="mr-2 h-4 w-4" /> Keyboard shortcuts
                </CommandItem>
              </CommandGroup>
              <CommandSeparator />
              <CommandGroup heading="Go to">
                {[
                  { label: "Inbox", to: "/mail/inbox", icon: Inbox },
                  { label: "Focused", to: "/mail/focused", icon: Inbox },
                  { label: "Drafts", to: "/mail/drafts", icon: FileEdit },
                  { label: "Sent", to: "/mail/sent", icon: Send },
                  { label: "Archive", to: "/mail/archive", icon: Archive },
                  { label: "Flagged", to: "/mail/flagged", icon: Flag },
                  { label: "Deleted", to: "/mail/deleted", icon: Trash2 },
                  { label: "Rules", to: "/rules", icon: Wand2 },
                  { label: "Templates", to: "/templates", icon: FileText },
                  { label: "Settings", to: "/settings/mail", icon: Settings },
                ].map((it) => {
                  const Icon = it.icon;
                  return (
                    <CommandItem
                      key={it.to}
                      onSelect={() => {
                        navigate({ to: it.to });
                        openPalette(false);
                      }}
                    >
                      <Icon className="mr-2 h-4 w-4" /> {it.label}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
              <CommandSeparator />
              <CommandGroup heading="Search">
                <CommandItem
                  onSelect={() => {
                    navigate({ to: "/mail/search", search: { q: "is:unread" } });
                    openPalette(false);
                  }}
                >
                  <Search className="mr-2 h-4 w-4" /> Unread mail
                </CommandItem>
                <CommandItem
                  onSelect={() => {
                    navigate({ to: "/mail/search", search: { q: "has:attachment" } });
                    openPalette(false);
                  }}
                >
                  <Search className="mr-2 h-4 w-4" /> Mail with attachments
                </CommandItem>
              </CommandGroup>
            </CommandList>
          </Command>
        </DialogContent>
      </Dialog>

      {/* New folder */}
      <Dialog open={newFolderOpen} onOpenChange={(v) => openNewFolder(v)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New folder</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="folder-name">Name</Label>
            <Input
              id="folder-name"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              placeholder="e.g. Investor relations"
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => openNewFolder(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!newFolderName.trim()) return;
                addFolder(newFolderName.trim());
                setNewFolderName("");
                openNewFolder(false);
                toast.success("Folder created");
              }}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Move to */}
      <Dialog open={moveToOpen} onOpenChange={(v) => openMoveTo(v)}>
        <DialogContent className="sm:max-w-md p-0">
          <DialogHeader className="px-4 pt-4">
            <DialogTitle>Move to folder</DialogTitle>
            <DialogDescription>
              Moving {targetIds.length} message{targetIds.length === 1 ? "" : "s"}.
            </DialogDescription>
          </DialogHeader>
          <Command>
            <CommandInput placeholder="Search folders…" />
            <CommandList className="max-h-[300px]">
              <CommandEmpty>No folders.</CommandEmpty>
              <CommandGroup heading="System">
                {folders
                  .filter((f) => !["focused", "other"].includes(f.id))
                  .map((f) => (
                    <CommandItem
                      key={f.id}
                      onSelect={() => {
                        moveTo(targetIds, f.id);
                        openMoveTo(false);
                        clearSelection();
                        toast.success(`Moved to ${f.name}`);
                      }}
                    >
                      <Folder className="mr-2 h-4 w-4" /> {f.name}
                    </CommandItem>
                  ))}
              </CommandGroup>
              <CommandGroup heading="Folders">
                {customFolders.map((f) => (
                  <CommandItem
                    key={f.id}
                    onSelect={() => {
                      moveTo(targetIds, f.id);
                      openMoveTo(false);
                      clearSelection();
                      toast.success(`Moved to ${f.name}`);
                    }}
                  >
                    <Folder className="mr-2 h-4 w-4" /> {f.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </DialogContent>
      </Dialog>

      {/* Snooze */}
      <Dialog open={snoozeOpen} onOpenChange={(v) => openSnooze(v)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Snooze message</DialogTitle>
            <DialogDescription>Bring it back to the top of your inbox later.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            {[
              { label: "Later today", offset: 4 * 3600_000 },
              { label: "Tomorrow", offset: 24 * 3600_000 },
              { label: "This weekend", offset: 3 * 24 * 3600_000 },
              { label: "Next week", offset: 7 * 24 * 3600_000 },
            ].map((p) => (
              <Button
                key={p.label}
                variant="outline"
                className="justify-start"
                onClick={() => {
                  snooze(targetIds, new Date(Date.now() + p.offset).toISOString());
                  openSnooze(false);
                  clearSelection();
                  toast.success(`Snoozed until ${p.label.toLowerCase()}`);
                }}
              >
                {p.label}
              </Button>
            ))}
          </div>
          <div className="rounded-md border border-border p-2">
            <Calendar mode="single" selected={snoozeDate} onSelect={setSnoozeDate} />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => openSnooze(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!snoozeDate) return;
                snooze(targetIds, snoozeDate.toISOString());
                openSnooze(false);
                clearSelection();
                toast.success("Snoozed");
              }}
            >
              Snooze
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Categorize */}
      <Dialog open={categorizeOpen} onOpenChange={(v) => openCategorize(v)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Categorize</DialogTitle>
          </DialogHeader>
          <div className="grid gap-1.5">
            {CATEGORIES.map((c) => {
              const s = CATEGORY_STYLES[c.color];
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => {
                    categorize(targetIds, c.id);
                    openCategorize(false);
                    clearSelection();
                    toast.success(`Categorized as ${c.name}`);
                  }}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-muted"
                >
                  <span className={cn("h-3 w-3 rounded-sm", s?.dot)} aria-hidden />
                  {c.name}
                </button>
              );
            })}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
