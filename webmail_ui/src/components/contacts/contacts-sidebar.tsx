import { Pin, Users, Plus } from "lucide-react";
import { useMemo } from "react";
import { useContactsStore } from "@/stores/contacts-store";
import { CONTACT_GROUPS, type ContactGroup } from "@/data/contacts";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

type Selection = ContactGroup | "all" | "pinned";

const FIXED: { id: Selection; label: string }[] = [
  { id: "all", label: "All contacts" },
  { id: "pinned", label: "Pinned" },
];

export function ContactsSidebar() {
  const contacts = useContactsStore((s) => s.contacts);
  const selected = useContactsStore((s) => s.selectedGroup);
  const setSelected = useContactsStore((s) => s.setSelectedGroup);

  const counts = useMemo(() => {
    const map: Record<string, number> = {
      all: contacts.length,
      pinned: contacts.filter((c) => c.pinned).length,
    };
    for (const g of CONTACT_GROUPS) {
      map[g.id] = contacts.filter((c) => c.group === g.id).length;
    }
    return map;
  }, [contacts]);

  return (
    <aside className="hidden w-56 shrink-0 flex-col gap-4 border-r border-border bg-sidebar p-3 text-sidebar-foreground md:flex">
      <header className="flex items-center justify-between px-2 pt-1">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4" aria-hidden />
          <h1 className="text-sm font-semibold">Contacts</h1>
        </div>
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
          aria-label="New contact"
          onClick={() => toast("New contact form is a placeholder in this demo")}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </header>

      <nav className="space-y-0.5">
        {FIXED.map((item) => (
          <SidebarRow
            key={item.id}
            active={selected === item.id}
            onClick={() => setSelected(item.id)}
            count={counts[item.id]}
            icon={item.id === "pinned" ? <Pin className="h-3.5 w-3.5" /> : null}
          >
            {item.label}
          </SidebarRow>
        ))}
      </nav>

      <div>
        <div className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wide text-sidebar-foreground/60">
          Groups
        </div>
        <nav className="space-y-0.5">
          {CONTACT_GROUPS.map((g) => (
            <SidebarRow
              key={g.id}
              active={selected === g.id}
              onClick={() => setSelected(g.id)}
              count={counts[g.id]}
            >
              {g.label}
            </SidebarRow>
          ))}
        </nav>
      </div>
    </aside>
  );
}

function SidebarRow({
  active,
  onClick,
  count,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  count: number;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm transition-colors",
        active
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "hover:bg-sidebar-accent/60",
      )}
    >
      <span className="flex min-w-0 items-center gap-2">
        {icon}
        <span className="truncate">{children}</span>
      </span>
      <span
        className={cn(
          "shrink-0 rounded-full px-1.5 text-[10px] tabular-nums",
          active ? "bg-sidebar/40" : "bg-sidebar-accent/60",
        )}
      >
        {count}
      </span>
    </button>
  );
}
