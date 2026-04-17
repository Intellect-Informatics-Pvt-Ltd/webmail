import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import {
  avatarColorFor,
  formatMailTime,
  initialsOf,
} from "@/lib/mail-format";
import type { MailMessage } from "@/types/mail";
import {
  Paperclip,
  Flag,
  Pin,
  AlertCircle,
  Archive,
  Trash2,
  Clock,
  ShieldCheck,
  AtSign,
} from "lucide-react";
import { CATEGORY_STYLES, getCategory } from "@/data/categories";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { usePrefsStore } from "@/stores/ui-store";

interface MessageRowProps {
  message: MailMessage;
  selected: boolean;
  active: boolean;
  onClick: () => void;
  onCheckedChange: (checked: boolean) => void;
  onArchive: () => void;
  onDelete: () => void;
  onToggleFlag: () => void;
  onSnooze: () => void;
}

export function MessageRow({
  message: m,
  selected,
  active,
  onClick,
  onCheckedChange,
  onArchive,
  onDelete,
  onToggleFlag,
  onSnooze,
}: MessageRowProps) {
  const density = usePrefsStore((s) => s.prefs.density);
  const previewLines = usePrefsStore((s) => s.prefs.previewLines);

  const py =
    density === "compact" ? "py-1.5" : density === "spacious" ? "py-3.5" : "py-2.5";

  return (
    <TooltipProvider delayDuration={400}>
      <div
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onClick();
          }
        }}
        className={cn(
          "group relative flex w-full cursor-pointer items-start gap-3 border-b border-border/60 px-3 transition-colors",
          py,
          active
            ? "bg-primary/8 ring-1 ring-inset ring-primary/30"
            : selected
              ? "bg-accent/60"
              : "hover:bg-muted/60",
        )}
      >
        {/* unread indicator bar */}
        {!m.isRead && !active && (
          <span
            className="absolute left-0 top-1/2 h-6 w-0.5 -translate-y-1/2 rounded-r bg-primary"
            aria-hidden
          />
        )}

        <div
          className="flex items-center pt-0.5"
          onClick={(e) => e.stopPropagation()}
        >
          <Checkbox
            checked={selected}
            onCheckedChange={(v) => onCheckedChange(Boolean(v))}
            aria-label={`Select ${m.subject}`}
            className="opacity-0 transition-opacity group-hover:opacity-100 data-[state=checked]:opacity-100"
          />
        </div>

        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback
            className={cn("text-xs text-white", avatarColorFor(m.sender.email))}
          >
            {initialsOf(m.sender.name)}
          </AvatarFallback>
        </Avatar>

        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <span
              className={cn(
                "truncate text-sm",
                m.isRead ? "text-foreground/85" : "font-semibold text-foreground",
              )}
            >
              {m.sender.name}
            </span>
            {m.importance === "high" && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <AlertCircle
                    className="h-3.5 w-3.5 shrink-0 text-destructive"
                    aria-label="High importance"
                  />
                </TooltipTrigger>
                <TooltipContent>High importance</TooltipContent>
              </Tooltip>
            )}
            {m.trustVerified && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <ShieldCheck
                    className="h-3.5 w-3.5 shrink-0 text-success"
                    aria-label="Verified sender"
                  />
                </TooltipTrigger>
                <TooltipContent>Verified sender</TooltipContent>
              </Tooltip>
            )}
            {m.hasMentions && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <AtSign
                    className="h-3.5 w-3.5 shrink-0 text-info"
                    aria-label="Mentions you"
                  />
                </TooltipTrigger>
                <TooltipContent>Mentions you</TooltipContent>
              </Tooltip>
            )}
            <span className="ml-auto whitespace-nowrap text-xs text-muted-foreground tabular-nums">
              {formatMailTime(m.receivedAt)}
            </span>
          </div>

          <div className="mt-0.5 flex items-center gap-1.5">
            <span
              className={cn(
                "truncate text-sm",
                m.isRead ? "text-foreground/80" : "font-medium text-foreground",
              )}
            >
              {m.subject || "(no subject)"}
            </span>
            {m.scheduledFor && (
              <span className="rounded-sm bg-info/10 px-1.5 text-[10px] font-medium uppercase tracking-wide text-info">
                Scheduled
              </span>
            )}
            {m.hasAttachments && (
              <Paperclip className="ml-auto h-3.5 w-3.5 text-muted-foreground" aria-label="Has attachments" />
            )}
          </div>

          <p
            className={cn(
              "mt-0.5 text-xs text-muted-foreground",
              previewLines === 1 ? "truncate" : `line-clamp-${previewLines}`,
            )}
          >
            {m.preview}
          </p>

          {m.categories.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {m.categories.map((cid) => {
                const c = getCategory(cid);
                if (!c) return null;
                const style = CATEGORY_STYLES[c.color];
                return (
                  <span
                    key={cid}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5 text-[10px] font-medium",
                      style?.chip ?? "bg-muted text-muted-foreground",
                    )}
                  >
                    <span className={cn("h-1.5 w-1.5 rounded-full", style?.dot)} aria-hidden />
                    {c.name}
                  </span>
                );
              })}
            </div>
          )}
        </div>

        {/* status icons (always visible) */}
        <div className="ml-1 flex flex-col items-center gap-1 pt-0.5">
          {m.isPinned && <Pin className="h-3.5 w-3.5 text-primary" aria-label="Pinned" />}
          {m.isFlagged && <Flag className="h-3.5 w-3.5 fill-warning text-warning" aria-label="Flagged" />}
        </div>

        {/* hover quick actions */}
        <div
          className="absolute right-2 top-1/2 hidden -translate-y-1/2 items-center gap-0.5 rounded-md border border-border bg-popover p-0.5 shadow-sm group-hover:flex"
          onClick={(e) => e.stopPropagation()}
        >
          <QuickActionBtn label="Archive" onClick={onArchive}>
            <Archive className="h-3.5 w-3.5" />
          </QuickActionBtn>
          <QuickActionBtn label="Delete" onClick={onDelete}>
            <Trash2 className="h-3.5 w-3.5" />
          </QuickActionBtn>
          <QuickActionBtn label={m.isFlagged ? "Unflag" : "Flag"} onClick={onToggleFlag}>
            <Flag className={cn("h-3.5 w-3.5", m.isFlagged && "fill-warning text-warning")} />
          </QuickActionBtn>
          <QuickActionBtn label="Snooze" onClick={onSnooze}>
            <Clock className="h-3.5 w-3.5" />
          </QuickActionBtn>
        </div>
      </div>
    </TooltipProvider>
  );
}

function QuickActionBtn({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={label}
          onClick={onClick}
          className="inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          {children}
        </button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}
