import { useMemo, useState } from "react";
import {
  Reply,
  ReplyAll,
  Forward,
  Archive,
  Trash2,
  FolderInput,
  Tag as TagIcon,
  Flag,
  Clock,
  MoreHorizontal,
  ChevronDown,
  ChevronRight,
  Paperclip,
  Download,
  ShieldCheck,
  AlertCircle,
  Inbox,
  X,
  FileText,
  Star,
  Printer,
} from "lucide-react";
import { useUIStore } from "@/stores/ui-store";
import { useMailStore } from "@/stores/mail-store";
import { useComposeStore } from "@/stores/compose-store";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CATEGORY_STYLES, getCategory } from "@/data/categories";
import {
  avatarColorFor,
  formatBytes,
  formatMailFullTime,
  initialsOf,
} from "@/lib/mail-format";
import { cn } from "@/lib/utils";
import type { MailMessage } from "@/types/mail";
import { toast } from "sonner";
import { SanitizedHtmlFrame } from "@/components/mail/sanitized-html-frame";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function ReadingPane() {
  const selectedThreadId = useUIStore((s) => s.selectedThreadId);
  const setSelectedThread = useUIStore((s) => s.setSelectedThread);
  const openMoveTo = useUIStore((s) => s.openMoveTo);
  const openSnooze = useUIStore((s) => s.openSnooze);
  const openCategorize = useUIStore((s) => s.openCategorize);
  const setSelectedRowIds = useUIStore((s) => s.setSelectedRowIds);

  const messages = useMailStore((s) => s.messages);
  const { archive, remove, toggleFlag } = useMailStore();
  const openCompose = useComposeStore((s) => s.openCompose);

  const [showCcBcc, setShowCcBcc] = useState(false);
  const [showMeta, setShowMeta] = useState(false);

  const thread = useMemo(() => {
    if (!selectedThreadId) return [];
    return messages
      .filter((m) => m.threadId === selectedThreadId)
      .sort(
        (a, b) =>
          new Date(a.receivedAt).getTime() - new Date(b.receivedAt).getTime(),
      );
  }, [messages, selectedThreadId]);

  if (!selectedThreadId || thread.length === 0) {
    return <EmptyReadingPane />;
  }

  const head = thread[thread.length - 1];
  const subject = head.subject.replace(/^Re:\s*/i, "");
  const ids = thread.map((m) => m.id);

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex h-full w-full min-w-0 flex-col bg-card">
        {/* Toolbar */}
        <div className="flex h-12 shrink-0 items-center gap-1 border-b border-border bg-card px-3">
          <ToolbarBtn
            icon={Reply}
            label="Reply"
            onClick={() =>
              openCompose({
                to: [head.sender],
                subject: subject.startsWith("Re:") ? subject : `Re: ${subject}`,
                bodyHtml: `<br/><br/><blockquote>${head.bodyHtml}</blockquote>`,
                inReplyToId: head.id,
              })
            }
          />
          <ToolbarBtn
            icon={ReplyAll}
            label="Reply all"
            onClick={() =>
              openCompose({
                to: [head.sender, ...head.recipients].filter(
                  (r) => r.email !== "avery@psense.ai",
                ),
                cc: head.cc ?? [],
                subject: subject.startsWith("Re:") ? subject : `Re: ${subject}`,
                bodyHtml: `<br/><br/><blockquote>${head.bodyHtml}</blockquote>`,
                inReplyToId: head.id,
              })
            }
          />
          <ToolbarBtn
            icon={Forward}
            label="Forward"
            onClick={() =>
              openCompose({
                subject: `Fwd: ${subject}`,
                bodyHtml: `<br/><br/><blockquote>${head.bodyHtml}</blockquote>`,
              })
            }
          />
          <Separator orientation="vertical" className="mx-1 h-5" />
          <ToolbarBtn
            icon={Archive}
            label="Archive"
            onClick={() => {
              archive(ids);
              setSelectedThread(null);
              toast.success("Archived");
            }}
          />
          <ToolbarBtn
            icon={Trash2}
            label="Delete"
            onClick={() => {
              remove(ids);
              setSelectedThread(null);
              toast.success("Moved to Deleted");
            }}
          />
          <ToolbarBtn
            icon={FolderInput}
            label="Move"
            onClick={() => {
              setSelectedRowIds(ids);
              openMoveTo(true);
            }}
          />
          <ToolbarBtn
            icon={TagIcon}
            label="Categorize"
            onClick={() => {
              setSelectedRowIds(ids);
              openCategorize(true);
            }}
          />
          <ToolbarBtn
            icon={Flag}
            label={head.isFlagged ? "Unflag" : "Flag"}
            onClick={() => toggleFlag(ids)}
          />
          <ToolbarBtn
            icon={Clock}
            label="Snooze"
            onClick={() => {
              setSelectedRowIds(ids);
              openSnooze(true);
            }}
          />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="More actions"
                className="h-8 w-8"
              >
                <MoreHorizontal className="h-4 w-4" aria-hidden />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-52">
              <DropdownMenuItem>
                <Star className="mr-2 h-4 w-4" /> Pin to top
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Printer className="mr-2 h-4 w-4" /> Print
              </DropdownMenuItem>
              <DropdownMenuItem>
                <FileText className="mr-2 h-4 w-4" /> Save as PDF
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setShowMeta((v) => !v)}>
                {showMeta ? "Hide details" : "Show details"}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-8 w-8"
            aria-label="Close"
            onClick={() => setSelectedThread(null)}
          >
            <X className="h-4 w-4" aria-hidden />
          </Button>
        </div>

        {/* Content */}
        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-3xl px-6 py-5">
            <h2 className="text-xl font-semibold leading-tight tracking-tight text-foreground">
              {subject || "(no subject)"}
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {head.categories.map((cid) => {
                const c = getCategory(cid);
                if (!c) return null;
                const s = CATEGORY_STYLES[c.color];
                return (
                  <span
                    key={cid}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-[11px] font-medium",
                      s?.chip,
                    )}
                  >
                    <span className={cn("h-1.5 w-1.5 rounded-full", s?.dot)} aria-hidden />
                    {c.name}
                  </span>
                );
              })}
              {head.importance === "high" && (
                <span className="inline-flex items-center gap-1 rounded-sm bg-destructive/10 px-1.5 py-0.5 text-[11px] font-medium text-destructive">
                  <AlertCircle className="h-3 w-3" aria-hidden /> High importance
                </span>
              )}
              {thread.length > 1 && (
                <span className="rounded-sm bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground tabular-nums">
                  {thread.length} messages
                </span>
              )}
            </div>

            <div className="mt-4 space-y-3">
              {thread.map((msg, idx) => (
                <ThreadMessage
                  key={msg.id}
                  msg={msg}
                  defaultOpen={idx === thread.length - 1}
                  showCcBcc={showCcBcc}
                  setShowCcBcc={setShowCcBcc}
                />
              ))}
            </div>

            {showMeta && <MetaPanel msg={head} />}
          </div>
        </ScrollArea>
      </div>
    </TooltipProvider>
  );
}

function ToolbarBtn({
  icon: Icon,
  label,
  onClick,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClick}
          className="h-8 gap-1.5 px-2 text-sm"
        >
          <Icon className="h-4 w-4" />
          <span className="hidden lg:inline">{label}</span>
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

function ThreadMessage({
  msg,
  defaultOpen,
  showCcBcc,
  setShowCcBcc,
}: {
  msg: MailMessage;
  defaultOpen: boolean;
  showCcBcc: boolean;
  setShowCcBcc: (v: boolean) => void;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const recipients = msg.recipients.map((r) => r.name || r.email).join(", ");

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-muted/40"
      >
        <Avatar className="h-9 w-9 shrink-0">
          <AvatarFallback
            className={cn("text-xs text-white", avatarColorFor(msg.sender.email))}
          >
            {initialsOf(msg.sender.name)}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">
              {msg.sender.name}
            </span>
            <span className="truncate text-xs text-muted-foreground">
              &lt;{msg.sender.email}&gt;
            </span>
            {msg.trustVerified && (
              <ShieldCheck
                className="h-3.5 w-3.5 shrink-0 text-success"
                aria-label="Verified"
              />
            )}
            <span className="ml-auto whitespace-nowrap text-xs text-muted-foreground tabular-nums">
              {formatMailFullTime(msg.receivedAt)}
            </span>
          </div>
          <div className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
            <span>to {recipients}</span>
            {(msg.cc?.length || msg.bcc?.length) && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowCcBcc(!showCcBcc);
                }}
                className="rounded px-1 text-primary hover:underline"
              >
                {showCcBcc ? "hide cc/bcc" : "show cc/bcc"}
              </button>
            )}
            {open ? (
              <ChevronDown className="ml-auto h-3.5 w-3.5" aria-hidden />
            ) : (
              <ChevronRight className="ml-auto h-3.5 w-3.5" aria-hidden />
            )}
          </div>
          {showCcBcc && (msg.cc?.length || msg.bcc?.length) && (
            <div className="mt-1 space-y-0.5 text-xs text-muted-foreground">
              {msg.cc && msg.cc.length > 0 && (
                <div>cc: {msg.cc.map((r) => r.email).join(", ")}</div>
              )}
              {msg.bcc && msg.bcc.length > 0 && (
                <div>bcc: {msg.bcc.map((r) => r.email).join(", ")}</div>
              )}
            </div>
          )}
        </div>
      </button>

      {open && (
        <div className="border-t border-border px-4 py-3">
          <SanitizedHtmlFrame
            bodyHtml={msg.bodyHtml}
            bodyText={undefined}
            className="prose prose-sm max-w-none text-sm leading-relaxed text-foreground/90"
          />

          {msg.attachments && msg.attachments.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Paperclip className="h-3.5 w-3.5" aria-hidden />
                {msg.attachments.length} attachment
                {msg.attachments.length === 1 ? "" : "s"}
              </div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {msg.attachments.map((a) => (
                  <div
                    key={a.id}
                    className="group flex items-center gap-3 rounded-md border border-border bg-background p-2.5 hover:border-primary/40"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-xs font-semibold uppercase text-primary">
                      {a.mime.slice(0, 4)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-foreground">
                        {a.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatBytes(a.size)}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Download ${a.name}`}
                      className="h-7 w-7 shrink-0 opacity-0 group-hover:opacity-100"
                    >
                      <Download className="h-3.5 w-3.5" aria-hidden />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetaPanel({ msg }: { msg: MailMessage }) {
  return (
    <div className="mt-4 rounded-lg border border-border bg-muted/40 p-4 text-xs text-muted-foreground">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-foreground/80">
        Message details
      </h3>
      <dl className="grid grid-cols-[120px_1fr] gap-y-1.5">
        <dt>Folder</dt>
        <dd className="text-foreground/80 capitalize">{msg.folderId}</dd>
        <dt>Thread ID</dt>
        <dd className="font-mono">{msg.threadId}</dd>
        <dt>Received</dt>
        <dd className="text-foreground/80">{formatMailFullTime(msg.receivedAt)}</dd>
        <dt>Categories</dt>
        <dd className="text-foreground/80">
          {msg.categories.length ? msg.categories.join(", ") : "—"}
        </dd>
        <dt>Retention</dt>
        <dd>Default — 7 years</dd>
        <dt>Encryption</dt>
        <dd>TLS in transit · at rest</dd>
      </dl>
    </div>
  );
}

function EmptyReadingPane() {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-muted/20 p-10 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-background shadow-sm ring-1 ring-border">
        <Inbox className="h-7 w-7 text-muted-foreground" aria-hidden />
      </div>
      <p className="mt-4 text-sm font-medium text-foreground">No message selected</p>
      <p className="mt-1 max-w-sm text-xs text-muted-foreground">
        Choose a message from the list to read it. Use{" "}
        <kbd className="rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-mono">
          j
        </kbd>{" "}
        and{" "}
        <kbd className="rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-mono">
          k
        </kbd>{" "}
        to navigate.
      </p>
    </div>
  );
}
