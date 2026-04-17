import { Link, useLocation } from "@tanstack/react-router";
import { Mail, Calendar, Users, ListChecks, MoreHorizontal } from "lucide-react";
import type { ComponentType } from "react";
import type { LucideProps } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type RailItem = {
  id: string;
  label: string;
  icon: ComponentType<LucideProps>;
  to?: "/mail/inbox" | "/calendar/week" | "/contacts";
  isActive?: (p: string) => boolean;
  disabled?: boolean;
};

const RAIL_ITEMS: RailItem[] = [
  {
    id: "mail",
    label: "Mail",
    icon: Mail,
    to: "/mail/inbox",
    isActive: (p) => p.startsWith("/mail") || p === "/",
  },
  {
    id: "calendar",
    label: "Calendar",
    icon: Calendar,
    to: "/calendar/week",
    isActive: (p) => p.startsWith("/calendar"),
  },
  {
    id: "contacts",
    label: "Contacts",
    icon: Users,
    to: "/contacts",
    isActive: (p) => p.startsWith("/contacts"),
  },
  { id: "tasks", label: "Tasks", icon: ListChecks, disabled: true },
];

export function AppRail() {
  const { pathname } = useLocation();

  return (
    <TooltipProvider delayDuration={300}>
      <aside
        aria-label="Workspace navigation"
        className="flex w-14 shrink-0 flex-col items-center gap-1 bg-rail py-3 text-rail-foreground"
      >
        {RAIL_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = item.isActive?.(pathname) ?? false;
          const inner = (
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                active ? "bg-rail-active text-primary-foreground" : "hover:bg-white/10",
                item.disabled && "opacity-50",
              )}
              aria-current={active ? "page" : undefined}
              aria-label={item.label}
            >
              <Icon className="h-5 w-5" aria-hidden />
            </div>
          );

          return (
            <Tooltip key={item.id}>
              <TooltipTrigger asChild>
                {item.disabled || !item.to ? (
                  <button type="button" className="cursor-not-allowed">
                    {inner}
                  </button>
                ) : (
                  <Link to={item.to}>{inner}</Link>
                )}
              </TooltipTrigger>
              <TooltipContent side="right">
                {item.label}
                {item.disabled && " — coming soon"}
              </TooltipContent>
            </Tooltip>
          );
        })}

        <div className="mt-auto">
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label="More apps"
                className="flex h-10 w-10 items-center justify-center rounded-lg hover:bg-white/10"
              >
                <MoreHorizontal className="h-5 w-5" aria-hidden />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">More apps</TooltipContent>
          </Tooltip>
        </div>
      </aside>
    </TooltipProvider>
  );
}
