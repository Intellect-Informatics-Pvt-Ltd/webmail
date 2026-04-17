import { useEffect, useMemo, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  Archive,
  Trash2,
  Clock,
  Flag,
  Tag as TagIcon,
  FolderInput,
  CheckSquare,
  RefreshCw,
  ArrowUpDown,
  Filter,
  Mail as MailIcon,
  MailOpen,
  Pin,
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useUIStore, type ListView } from "@/stores/ui-store";
import { useMailStore } from "@/stores/mail-store";
import { MessageRow } from "./message-row";
import { groupKeyOf, type GroupKey } from "@/lib/mail-format";
import type { MailMessage } from "@/types/mail";
import { useFilteredMessages, type MessageFilter } from "@/hooks/use-filtered-messages";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface MessageListProps {
  filter: MessageFilter;
  title: string;
  description?: string;
}

const VIEWS: { id: ListView; label: string }[] = [
  { id: "all", label: "All" },
  { id: "unread", label: "Unread" },
  { id: "focused", label: "Focused" },
  { id: "other", label: "Other" },
  { id: "attachments", label: "Attachments" },
  { id: "mentions", label: "Mentions" },
];

export function MessageList({ filter, title, description }: MessageListProps) {
  const navigate = useNavigate();
  const messages = useFilteredMessages(filter);
  const listView = useUIStore((s) => s.listView);
  const setListView = useUIStore((s) => s.setListView);
  const selectedRowIds = useUIStore((s) => s.selectedRowIds);
  const setSelectedRowIds = useUIStore((s) => s.setSelectedRowIds);
  const toggleRowSelected = useUIStore((s) => s.toggleRowSelected);
  const clearSelection = useUIStore((s) => s.clearSelection);
  const selectedThreadId = useUIStore((s) => s.selectedThreadId);
  const setSelectedThread = useUIStore((s) => s.setSelectedThread);
  const openMoveTo = useUIStore((s) => s.openMoveTo);
  const openSnooze = useUIStore((s) => s.openSnooze);
  const openCategorize = useUIStore((s) => s.openCategorize);

  const { archive, remove, toggleFlag, toggleRead, snooze } = useMailStore();

  // group by date
  const grouped = useMemo(() => {
    const groups: Record<GroupKey, MailMessage[]> = {
      Today: [],
      Yesterday: [],
      "Earlier this week": [],
      Older: [],
    };
    for (const m of messages) groups[groupKeyOf(m.receivedAt)].push(m);
    return groups;
  }, [messages]);

  // clear selection when filter changes
  const lastKey = useRef("");
  useEffect(() => {
    const key = JSON.stringify({ ...filter, listView });
    if (key !== lastKey.current) {
      lastKey.current = key;
      clearSelection();
    }
  }, [filter, listView, clearSelection]);

  // keyboard navigation
  const navigateMessage = (delta: 1 | -1) => {
    if (messages.length === 0) return;
    const idx = messages.findIndex((m) => m.threadId === selectedThreadId);
    const next = Math.max(0, Math.min(messages.length - 1, idx === -1 ? 0 : idx + delta));
    const target = messages[next];
    if (target) {
      setSelectedThread(target.threadId);
      toggleRead([target.id], true);
    }
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (
        t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          (t as HTMLElement).isContentEditable)
      )
        return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      switch (e.key) {
        case "j":
          e.preventDefault();
          navigateMessage(1);
          break;
        case "k":
          e.preventDefault();
          navigateMessage(-1);
          break;
        case "e":
          if (selectedThreadId) {
            e.preventDefault();
            const ids = messages.filter((m) => m.threadId === selectedThreadId).map((m) => m.id);
            archive(ids);
            setSelectedThread(null);
            toast.success("Archived", {
              action: { label: "Undo", onClick: () => {} },
            });
          }
          break;
        case "#":
        case "Delete":
          if (selectedThreadId) {
            e.preventDefault();
            const ids = messages.filter((m) => m.threadId === selectedThreadId).map((m) => m.id);
            remove(ids);
            setSelectedThread(null);
            toast.success("Moved to Deleted");
          }
          break;
        case "u":
          if (selectedThreadId) {
            e.preventDefault();
            const ids = messages.filter((m) => m.threadId === selectedThreadId).map((m) => m.id);
            toggleRead(ids);
          }
          break;
        case "f":
          if (selectedThreadId) {
            e.preventDefault();
            const ids = messages.filter((m) => m.threadId === selectedThreadId).map((m) => m.id);
            toggleFlag(ids);
          }
          break;
        case "/":
          e.preventDefault();
          (document.querySelector('input[aria-label="Search mail"]') as HTMLInputElement)?.focus();
          break;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [
    messages,
    selectedThreadId,
    archive,
    remove,
    toggleFlag,
    toggleRead,
    setSelectedThread,
  ]);

  const allSelected =
    messages.length > 0 && selectedRowIds.length === messages.length;
  const someSelected = selectedRowIds.length > 0 && !allSelected;

  function selectAll(v: boolean) {
    setSelectedRowIds(v ? messages.map((m) => m.id) : []);
  }

  function bulkArchive() {
    archive(selectedRowIds);
    toast.success(`Archived ${selectedRowIds.length} item${selectedRowIds.length === 1 ? "" : "s"}`);
    clearSelection();
  }
  function bulkDelete() {
    remove(selectedRowIds);
    toast.success(`Moved ${selectedRowIds.length} to Deleted`);
    clearSelection();
  }
  function bulkRead(read: boolean) {
    toggleRead(selectedRowIds, read);
    clearSelection();
  }
  function bulkFlag() {
    toggleFlag(selectedRowIds);
    clearSelection();
  }

  return (
    <div className="flex h-full w-full min-w-0 flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border bg-background/95 px-4 pb-2 pt-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <div className="flex items-center gap-2">
          <h1 className="text-base font-semibold leading-tight tracking-tight text-foreground">
            {title}
          </h1>
          <span className="rounded-md bg-muted px-1.5 py-0.5 text-xs tabular-nums text-muted-foreground">
            {messages.length}
          </span>
          <div className="ml-auto flex items-center gap-1">
            <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-muted-foreground">
              <RefreshCw className="h-3.5 w-3.5" aria-hidden />
              <span className="text-xs">Refresh</span>
            </Button>
            <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-muted-foreground">
              <Filter className="h-3.5 w-3.5" aria-hidden />
              <span className="text-xs">Filter</span>
            </Button>
            <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-muted-foreground">
              <ArrowUpDown className="h-3.5 w-3.5" aria-hidden />
              <span className="text-xs">Sort</span>
            </Button>
          </div>
        </div>
        {description && (
          <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
        )}

        <Tabs
          value={listView}
          onValueChange={(v) => setListView(v as ListView)}
          className="mt-2"
        >
          <TabsList className="h-8 bg-transparent p-0">
            {VIEWS.map((v) => (
              <TabsTrigger
                key={v.id}
                value={v.id}
                className="h-8 rounded-none border-b-2 border-transparent bg-transparent px-2.5 text-xs font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none"
              >
                {v.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* Bulk toolbar */}
      <div
        className={cn(
          "flex h-9 items-center gap-1 border-b border-border bg-muted/40 px-3 transition-all",
          selectedRowIds.length === 0 && "h-0 overflow-hidden border-b-0",
        )}
      >
        <Checkbox
          checked={allSelected ? true : someSelected ? "indeterminate" : false}
          onCheckedChange={(v) => selectAll(Boolean(v))}
          aria-label="Select all"
        />
        <span className="ml-2 text-xs text-muted-foreground">
          {selectedRowIds.length} selected
        </span>
        <Separator orientation="vertical" className="mx-2 h-4" />
        <BulkBtn icon={Archive} label="Archive" onClick={bulkArchive} />
        <BulkBtn icon={Trash2} label="Delete" onClick={bulkDelete} />
        <BulkBtn
          icon={FolderInput}
          label="Move"
          onClick={() => openMoveTo(true)}
        />
        <BulkBtn
          icon={TagIcon}
          label="Categorize"
          onClick={() => openCategorize(true)}
        />
        <BulkBtn icon={Flag} label="Flag" onClick={bulkFlag} />
        <BulkBtn icon={Clock} label="Snooze" onClick={() => openSnooze(true)} />
        <BulkBtn icon={MailOpen} label="Mark read" onClick={() => bulkRead(true)} />
        <BulkBtn icon={MailIcon} label="Mark unread" onClick={() => bulkRead(false)} />
        <Button
          variant="ghost"
          size="sm"
          onClick={clearSelection}
          className="ml-auto h-7 px-2 text-xs"
        >
          Clear
        </Button>
      </div>

      {/* List */}
      <ScrollArea className="flex-1">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          (Object.keys(grouped) as GroupKey[]).map((g) => {
            const items = grouped[g];
            if (items.length === 0) return null;
            return (
              <div key={g}>
                <div className="sticky top-0 z-10 flex items-center gap-2 border-b border-border bg-background/90 px-3 py-1.5 backdrop-blur">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    {g}
                  </span>
                  <span className="text-[10px] text-muted-foreground/70 tabular-nums">
                    {items.length}
                  </span>
                </div>
                {items.map((m) => (
                  <MessageRow
                    key={m.id}
                    message={m}
                    selected={selectedRowIds.includes(m.id)}
                    active={m.threadId === selectedThreadId}
                    onClick={() => {
                      setSelectedThread(m.threadId);
                      toggleRead([m.id], true);
                    }}
                    onCheckedChange={() => toggleRowSelected(m.id)}
                    onArchive={() => {
                      archive([m.id]);
                      toast.success("Archived");
                    }}
                    onDelete={() => {
                      remove([m.id]);
                      toast.success("Moved to Deleted");
                    }}
                    onToggleFlag={() => toggleFlag([m.id])}
                    onSnooze={() => {
                      setSelectedRowIds([m.id]);
                      openSnooze(true);
                    }}
                  />
                ))}
              </div>
            );
          })
        )}
      </ScrollArea>
    </div>
  );
}

function BulkBtn({
  icon: Icon,
  label,
  onClick,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={onClick}
      className="h-7 gap-1 px-2 text-xs text-foreground/85 hover:bg-background"
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </Button>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full min-h-[300px] flex-col items-center justify-center gap-3 px-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
        <CheckSquare className="h-6 w-6 text-muted-foreground" aria-hidden />
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">You're all caught up</p>
        <p className="mt-1 text-xs text-muted-foreground">
          No messages match this view. Try changing the tab above or check another folder.
        </p>
      </div>
    </div>
  );
}

// Avoid unused warning for Pin import (kept for future reorder)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const _Pin = Pin;
