import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  Search,
  Bell,
  HelpCircle,
  Settings,
  PenSquare,
  Sun,
  Moon,
  Keyboard,
  Command as CommandIcon,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PsenseLogo } from "@/components/psense-logo";
import { useComposeStore } from "@/stores/compose-store";
import { useUIStore, usePrefsStore } from "@/stores/ui-store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { initialsOf } from "@/lib/mail-format";

const SEARCH_TIPS = [
  { hint: "from:priya", desc: "Sender" },
  { hint: "to:me", desc: "Recipient" },
  { hint: "has:attachment", desc: "Attachments" },
  { hint: "is:unread", desc: "Unread" },
  { hint: "is:flagged", desc: "Flagged" },
  { hint: "subject:proposal", desc: "Subject keyword" },
  { hint: "after:2026/01/01", desc: "Date range" },
];

export function AppHeader() {
  const navigate = useNavigate();
  const openCompose = useComposeStore((s) => s.openCompose);
  const openShortcuts = useUIStore((s) => s.openShortcuts);
  const openPalette = useUIStore((s) => s.openPalette);
  const theme = usePrefsStore((s) => s.prefs.theme);
  const setTheme = usePrefsStore((s) => s.setTheme);

  const [q, setQ] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  function submitSearch(query: string) {
    setSearchOpen(false);
    navigate({ to: "/mail/search", search: { q: query } });
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-background pl-3 pr-4">
      {/* Logo */}
      <Link to="/mail/inbox" className="flex items-center gap-2 pr-2">
        <PsenseLogo className="h-7 w-auto" />
      </Link>

      {/* Search */}
      <div className="ml-2 max-w-2xl flex-1">
        <Popover open={searchOpen} onOpenChange={setSearchOpen}>
          <PopoverTrigger asChild>
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onFocus={() => setSearchOpen(true)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submitSearch(q);
                  if (e.key === "Escape") setSearchOpen(false);
                }}
                placeholder="Search mail and people"
                aria-label="Search mail"
                className="h-9 rounded-md bg-muted/60 pl-9 pr-20 text-sm shadow-none focus-visible:bg-background"
              />
              <kbd className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 select-none items-center gap-1 rounded border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground sm:inline-flex">
                /
              </kbd>
            </div>
          </PopoverTrigger>
          <PopoverContent
            align="start"
            sideOffset={6}
            className="w-[var(--radix-popover-trigger-width)] p-2"
            onOpenAutoFocus={(e) => e.preventDefault()}
          >
            <div className="px-2 py-1 text-xs font-medium text-muted-foreground">Recent</div>
            {["Northwind", "from:priya", "is:flagged invoice", "Q1 board deck"].map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => {
                  setQ(r);
                  submitSearch(r);
                }}
                className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted"
              >
                <Search className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                <span className="truncate">{r}</span>
              </button>
            ))}
            <div className="mt-2 border-t border-border pt-2">
              <div className="px-2 py-1 text-xs font-medium text-muted-foreground">
                Search syntax
              </div>
              <div className="grid grid-cols-2 gap-1 px-1">
                {SEARCH_TIPS.map((t) => (
                  <button
                    key={t.hint}
                    type="button"
                    onClick={() => setQ((curr) => `${curr ? curr + " " : ""}${t.hint}`)}
                    className="flex flex-col items-start rounded-md px-2 py-1 text-left hover:bg-muted"
                  >
                    <code className="text-xs text-primary">{t.hint}</code>
                    <span className="text-[11px] text-muted-foreground">{t.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          </PopoverContent>
        </Popover>
      </div>

      <Button
        variant="ghost"
        size="sm"
        onClick={() => openPalette(true)}
        className="hidden gap-1.5 text-muted-foreground md:inline-flex"
      >
        <CommandIcon className="h-3.5 w-3.5" aria-hidden />
        <span className="text-xs">⌘K</span>
      </Button>

      <div className="flex items-center gap-1">
        <Button
          onClick={() => openCompose()}
          size="sm"
          className="h-9 gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <PenSquare className="h-4 w-4" aria-hidden />
          <span className="hidden md:inline">Compose</span>
        </Button>

        <Button
          variant="ghost"
          size="icon"
          aria-label="Notifications"
          className="relative h-9 w-9"
        >
          <Bell className="h-4 w-4" aria-hidden />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-primary" />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          aria-label="Toggle theme"
          className="h-9 w-9"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" aria-hidden />
          ) : (
            <Moon className="h-4 w-4" aria-hidden />
          )}
        </Button>

        <Button
          variant="ghost"
          size="icon"
          aria-label="Keyboard shortcuts"
          className="h-9 w-9"
          onClick={() => openShortcuts(true)}
        >
          <Keyboard className="h-4 w-4" aria-hidden />
        </Button>

        <Button variant="ghost" size="icon" aria-label="Help" className="h-9 w-9">
          <HelpCircle className="h-4 w-4" aria-hidden />
        </Button>

        <Link
          to="/settings/mail"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-foreground hover:bg-accent hover:text-accent-foreground"
          aria-label="Settings"
        >
          <Settings className="h-4 w-4" aria-hidden />
        </Link>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="ml-1 inline-flex items-center gap-1 rounded-md p-1 hover:bg-accent"
              aria-label="Account"
            >
              <Avatar className="h-7 w-7">
                <AvatarFallback className="bg-primary text-xs text-primary-foreground">
                  {initialsOf("Avery Chen")}
                </AvatarFallback>
              </Avatar>
              <ChevronDown className="h-3 w-3 text-muted-foreground" aria-hidden />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span className="text-sm font-medium">Avery Chen</span>
                <span className="text-xs font-normal text-muted-foreground">
                  avery@psense.ai
                </span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/settings/preferences">Preferences</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/settings/mail">Mail settings</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/settings/signatures">Signatures</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/settings/accounts">Accounts & sync</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/rules">Rules</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/templates">Templates</Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => openShortcuts(true)}>
              Keyboard shortcuts
            </DropdownMenuItem>
            <DropdownMenuItem className="text-muted-foreground">Sign out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
