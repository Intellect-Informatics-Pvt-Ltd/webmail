import { useMemo, useState, useEffect, useCallback } from "react";
import { Link, useLocation, useNavigate } from "@tanstack/react-router";
import {
  Inbox,
  Star,
  Send,
  FileEdit,
  Archive,
  Clock,
  Flag,
  Trash2,
  AlertTriangle,
  Folder,
  ChevronDown,
  ChevronRight,
  Plus,
  Tag,
  PenSquare,
  Focus as FocusIcon,
  Layers,
  HardDrive,
  MoreHorizontal,
  Loader2,
} from "lucide-react";
import type { ComponentType } from "react";
import type { LucideProps } from "lucide-react";
import { cn } from "@/lib/utils";
import { useMailStore } from "@/stores/mail-store";
import { useUIStore } from "@/stores/ui-store";
import { useComposeStore } from "@/stores/compose-store";
import { CATEGORIES, CATEGORY_STYLES } from "@/data/categories";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type SystemItem = {
  id: string;
  label: string;
  icon: ComponentType<LucideProps>;
  href: string;
  countOf?: "unread" | "drafts" | "scheduled";
};

const PRIMARY: SystemItem[] = [
  { id: "inbox", label: "Inbox", icon: Inbox, href: "/mail/inbox", countOf: "unread" },
  { id: "focused", label: "Focused", icon: FocusIcon, href: "/mail/focused", countOf: "unread" },
  { id: "other", label: "Other", icon: Layers, href: "/mail/other", countOf: "unread" },
  { id: "drafts", label: "Drafts", icon: FileEdit, href: "/mail/drafts", countOf: "drafts" },
  { id: "sent", label: "Sent", icon: Send, href: "/mail/sent" },
  { id: "archive", label: "Archive", icon: Archive, href: "/mail/archive" },
  { id: "snoozed", label: "Snoozed", icon: Clock, href: "/mail/snoozed" },
  { id: "flagged", label: "Flagged", icon: Flag, href: "/mail/flagged" },
  { id: "deleted", label: "Deleted", icon: Trash2, href: "/mail/deleted" },
  { id: "junk", label: "Junk", icon: AlertTriangle, href: "/mail/junk" },
];

function NavRow({
  href,
  label,
  icon: Icon,
  count,
  active,
  onContext,
}: {
  href: string;
  label: string;
  icon: ComponentType<LucideProps>;
  count?: number;
  active: boolean;
  onContext?: () => void;
}) {
  return (
    <Link
      to={href}
      onContextMenu={(e) => {
        if (onContext) {
          e.preventDefault();
          onContext();
        }
      }}
      className={cn(
        "group flex h-8 items-center gap-2 rounded-md px-2 text-sm transition-colors",
        active
          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
          : "text-sidebar-foreground/85 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      <span className="truncate">{label}</span>
      {count !== undefined && count > 0 && (
        <span
          className={cn(
            "ml-auto rounded-full px-1.5 text-xs tabular-nums",
            active
              ? "bg-primary/20 text-sidebar-accent-foreground"
              : "text-sidebar-foreground/70",
          )}
        >
          {count}
        </span>
      )}
    </Link>
  );
}

function SectionHeader({
  label,
  open,
  onToggle,
  action,
}: {
  label: string;
  open: boolean;
  onToggle: () => void;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex h-7 items-center gap-1 px-2 text-xs uppercase tracking-wide text-sidebar-foreground/55">
      <button
        type="button"
        onClick={onToggle}
        className="flex flex-1 items-center gap-1 hover:text-sidebar-foreground/80"
      >
        {open ? (
          <ChevronDown className="h-3 w-3" aria-hidden />
        ) : (
          <ChevronRight className="h-3 w-3" aria-hidden />
        )}
        <span>{label}</span>
      </button>
      {action}
    </div>
  );
}

export function MailSidebar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const messages = useMailStore((s) => s.messages);
  const customFolders = useMailStore((s) => s.customFolders);
  const favorites = useMailStore((s) => s.favorites);
  const toggleFavorite = useMailStore((s) => s.toggleFavorite);
  const deleteFolder = useMailStore((s) => s.deleteFolder);
  const openCompose = useComposeStore((s) => s.openCompose);
  const openNewFolder = useUIStore((s) => s.openNewFolder);

  const [favOpen, setFavOpen] = useState(true);
  const [foldersOpen, setFoldersOpen] = useState(true);
  const [catsOpen, setCatsOpen] = useState(true);

  const counts = useMemo(() => {
    const unreadByFolder: Record<string, number> = {};
    let drafts = 0;
    let flagged = 0;
    let snoozed = 0;
    let focusedUnread = 0;
    let otherUnread = 0;
    for (const m of messages) {
      if (m.folderId === "drafts") drafts++;
      if (m.folderId === "snoozed") snoozed++;
      if (m.isFlagged) flagged++;
      if (!m.isRead && m.folderId !== "sent" && m.folderId !== "drafts") {
        unreadByFolder[m.folderId] = (unreadByFolder[m.folderId] ?? 0) + 1;
        if (m.folderId === "inbox") {
          if (m.isFocused) focusedUnread++;
          else otherUnread++;
        }
      }
    }
    return { unreadByFolder, drafts, flagged, snoozed, focusedUnread, otherUnread };
  }, [messages]);

  function getCount(item: SystemItem) {
    if (item.id === "focused") return counts.focusedUnread;
    if (item.id === "other") return counts.otherUnread;
    if (item.id === "flagged") return counts.flagged;
    if (item.id === "snoozed") return counts.snoozed;
    if (item.countOf === "drafts") return counts.drafts;
    if (item.countOf === "unread") return counts.unreadByFolder[item.id] ?? 0;
    return undefined;
  }

  const allFolders = [
    ...PRIMARY.map((p) => ({ id: p.id, name: p.label, href: p.href })),
    ...customFolders.map((f) => ({ id: f.id, name: f.name, href: `/mail/folder/${f.id}` })),
  ];

  return (
    <aside
      aria-label="Mail folders"
      className="flex w-64 shrink-0 flex-col bg-sidebar text-sidebar-foreground"
    >
      <div className="flex items-center gap-2 px-3 pt-3">
        <Button
          onClick={() => openCompose()}
          className="w-full justify-start gap-2 bg-primary text-primary-foreground shadow-sm hover:bg-primary/90"
        >
          <PenSquare className="h-4 w-4" aria-hidden />
          New message
        </Button>
      </div>

      <ScrollArea className="mt-3 flex-1 px-2">
        <div className="space-y-3 pb-4">
          {/* Favorites */}
          <div>
            <SectionHeader
              label="Favorites"
              open={favOpen}
              onToggle={() => setFavOpen((v) => !v)}
              action={
                <Star className="h-3 w-3 text-sidebar-foreground/50" aria-hidden />
              }
            />
            {favOpen && (
              <div className="mt-1 space-y-0.5">
                {favorites.length === 0 && (
                  <p className="px-2 text-xs text-sidebar-foreground/50">
                    Right-click a folder to favorite it.
                  </p>
                )}
                {favorites.map((favId) => {
                  const f = allFolders.find((x) => x.id === favId);
                  if (!f) return null;
                  const sys = PRIMARY.find((p) => p.id === favId);
                  const Icon = sys?.icon ?? Folder;
                  const count = sys ? getCount(sys) : undefined;
                  return (
                    <NavRow
                      key={favId}
                      href={f.href}
                      label={f.name}
                      icon={Icon}
                      count={count}
                      active={pathname === f.href}
                    />
                  );
                })}
              </div>
            )}
          </div>

          {/* System folders */}
          <div className="space-y-0.5">
            {PRIMARY.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.id === "inbox" && pathname === "/mail") ||
                (item.id === "inbox" && pathname === "/");
              return (
                <NavRow
                  key={item.id}
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  count={getCount(item)}
                  active={isActive}
                  onContext={() => toggleFavorite(item.id)}
                />
              );
            })}
          </div>

          {/* Custom folders */}
          <div>
            <SectionHeader
              label="Folders"
              open={foldersOpen}
              onToggle={() => setFoldersOpen((v) => !v)}
              action={
                <button
                  type="button"
                  className="rounded-sm p-0.5 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                  onClick={() => openNewFolder(true)}
                  aria-label="New folder"
                >
                  <Plus className="h-3 w-3" aria-hidden />
                </button>
              }
            />
            {foldersOpen && (
              <div className="mt-1 space-y-0.5">
                {customFolders.length === 0 && (
                  <p className="px-2 text-xs text-sidebar-foreground/50">No folders yet.</p>
                )}
                {customFolders.map((f) => {
                  const href = `/mail/folder/${f.id}`;
                  const active = pathname === href;
                  const isFav = favorites.includes(f.id);
                  return (
                    <div key={f.id} className="group/row relative">
                      <NavRow
                        href={href}
                        label={f.name}
                        icon={Folder}
                        count={counts.unreadByFolder[f.id]}
                        active={active}
                      />
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button
                            type="button"
                            className="absolute right-1 top-1 hidden rounded-sm p-1 text-sidebar-foreground/70 hover:bg-sidebar-accent group-hover/row:block"
                            aria-label={`Actions for ${f.name}`}
                            onClick={(e) => e.preventDefault()}
                          >
                            <MoreHorizontal className="h-3 w-3" aria-hidden />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-44">
                          <DropdownMenuItem onClick={() => toggleFavorite(f.id)}>
                            <Star className="mr-2 h-4 w-4" aria-hidden />
                            {isFav ? "Remove favorite" : "Add to favorites"}
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => openNewFolder(true)}>
                            <Plus className="mr-2 h-4 w-4" aria-hidden /> New folder
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => {
                              deleteFolder(f.id);
                              if (active) navigate({ to: "/mail/inbox" });
                            }}
                            className="text-destructive focus:text-destructive"
                          >
                            <Trash2 className="mr-2 h-4 w-4" aria-hidden /> Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Categories */}
          <div>
            <SectionHeader
              label="Categories"
              open={catsOpen}
              onToggle={() => setCatsOpen((v) => !v)}
              action={
                <Tag className="h-3 w-3 text-sidebar-foreground/50" aria-hidden />
              }
            />
            {catsOpen && (
              <div className="mt-1 space-y-0.5">
                {CATEGORIES.map((c) => {
                  const href = `/mail/category/${c.id}`;
                  const active = pathname === href;
                  const dot = CATEGORY_STYLES[c.color]?.dot ?? "bg-primary";
                  return (
                    <Link
                      key={c.id}
                      to={href}
                      className={cn(
                        "flex h-8 items-center gap-2 rounded-md px-2 text-sm",
                        active
                          ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                          : "text-sidebar-foreground/85 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                      )}
                    >
                      <span className={cn("h-2.5 w-2.5 rounded-sm", dot)} aria-hidden />
                      <span className="truncate">{c.name}</span>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </ScrollArea>

      {/* Sync status (POP3 only) */}
      <SyncStatusRow />

      {/* Storage info */}
      <div className="border-t border-sidebar-border p-3 text-xs text-sidebar-foreground/70">
        <div className="mb-1 flex items-center gap-2">
          <HardDrive className="h-3.5 w-3.5" aria-hidden />
          <span className="text-sidebar-foreground/85">Storage</span>
          <span className="ml-auto tabular-nums">38.2 / 100 GB</span>
        </div>
        <div className="h-1 overflow-hidden rounded-full bg-sidebar-border">
          <div className="h-full w-[38%] rounded-full bg-primary" />
        </div>
      </div>
    </aside>
  );
}

// ── Sync status row (shown when POP3 provider is active) ─────────────────────

interface SyncStatus {
  last_poll_at: string | null;
  last_poll_status: string;
  last_error: string | null;
  messages_last_cycle: number;
  is_polling: boolean;
}

function SyncStatusRow() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [visible, setVisible] = useState(false);

  const fetchStatus = useCallback(() => {
    fetch("/api/v1/accounts/pop3/status")
      .then((r) => {
        if (!r.ok) return null;
        return r.json();
      })
      .then((data: SyncStatus | null) => {
        if (data && data.last_poll_status !== "never") {
          setStatus(data);
          setVisible(true);
        }
      })
      .catch(() => setVisible(false));
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  if (!visible || !status) return null;

  const handleRetry = () => {
    fetch("/api/v1/accounts/pop3/sync", { method: "POST" }).catch(() => {});
    setTimeout(fetchStatus, 2000);
  };

  const formatRelative = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const min = Math.floor(diff / 60000);
    if (min < 1) return "just now";
    if (min < 60) return `${min} min ago`;
    const hrs = Math.floor(min / 60);
    return hrs < 24 ? `${hrs}h ago` : `${Math.floor(hrs / 24)}d ago`;
  };

  if (status.is_polling) {
    return (
      <div className="border-t border-sidebar-border px-3 py-2 text-xs text-sidebar-foreground/70">
        <div className="flex items-center gap-2">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Syncing\u2026</span>
        </div>
      </div>
    );
  }

  if (status.last_poll_status === "error") {
    return (
      <div className="border-t border-sidebar-border px-3 py-2 text-xs">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-destructive" />
          <span className="text-destructive">Sync error</span>
          <button
            onClick={handleRetry}
            className="ml-auto text-[10px] font-medium text-primary hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t border-sidebar-border px-3 py-2 text-xs text-sidebar-foreground/70">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        <span>
          Synced \u00b7 {status.last_poll_at ? formatRelative(status.last_poll_at) : "never"}
        </span>
      </div>
    </div>
  );
}
