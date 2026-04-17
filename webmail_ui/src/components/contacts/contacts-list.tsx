import { Link, useParams } from "@tanstack/react-router";
import { Pin, Search } from "lucide-react";
import { useMemo } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { initialsOf, avatarColorFor } from "@/lib/mail-format";
import { useContactsStore } from "@/stores/contacts-store";
import { CONTACT_GROUPS } from "@/data/contacts";
import { cn } from "@/lib/utils";

export function ContactsList() {
  const contacts = useContactsStore((s) => s.contacts);
  const selected = useContactsStore((s) => s.selectedGroup);
  const query = useContactsStore((s) => s.query);
  const setQuery = useContactsStore((s) => s.setQuery);
  const params = useParams({ strict: false }) as { contactId?: string };
  const activeId = params.contactId;

  const filtered = useMemo(() => {
    let list = contacts;
    if (selected === "pinned") list = list.filter((c) => c.pinned);
    else if (selected !== "all") list = list.filter((c) => c.group === selected);
    const q = query.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.email.toLowerCase().includes(q) ||
          (c.company?.toLowerCase().includes(q) ?? false),
      );
    }
    return [...list].sort((a, b) => {
      if (!!a.pinned !== !!b.pinned) return a.pinned ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
  }, [contacts, selected, query]);

  const heading =
    selected === "all"
      ? "All contacts"
      : selected === "pinned"
        ? "Pinned"
        : (CONTACT_GROUPS.find((g) => g.id === selected)?.label ?? "Contacts");

  return (
    <section className="flex w-full max-w-sm shrink-0 flex-col border-r border-border bg-background">
      <header className="space-y-2 border-b border-border p-3">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-semibold">{heading}</h2>
          <span className="text-xs text-muted-foreground tabular-nums">
            {filtered.length}
          </span>
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search name, email, company"
            className="h-8 pl-7 text-sm"
          />
        </div>
      </header>

      <ScrollArea className="flex-1">
        {filtered.length === 0 ? (
          <div className="p-6 text-center text-sm text-muted-foreground">
            No contacts found.
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {filtered.map((c) => {
              const isActive = c.id === activeId;
              return (
                <li key={c.id}>
                  <Link
                    to="/contacts/$contactId"
                    params={{ contactId: c.id }}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 transition-colors hover:bg-muted/60",
                      isActive && "bg-primary/10",
                    )}
                  >
                    <Avatar className="h-9 w-9 shrink-0">
                      <AvatarFallback
                        className={`${avatarColorFor(c.email)} text-xs font-semibold text-white`}
                      >
                        {initialsOf(c.name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={cn(
                            "truncate text-sm font-medium",
                            isActive && "text-primary",
                          )}
                        >
                          {c.name}
                        </span>
                        {c.pinned && (
                          <Pin
                            className="h-3 w-3 shrink-0 text-muted-foreground"
                            aria-label="Pinned"
                          />
                        )}
                      </div>
                      <div className="truncate text-xs text-muted-foreground">
                        {c.role && c.company
                          ? `${c.role} · ${c.company}`
                          : (c.company ?? c.email)}
                      </div>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </ScrollArea>
    </section>
  );
}
