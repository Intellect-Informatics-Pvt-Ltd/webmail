import type { MailCategory } from "@/types/mail";

export const CATEGORIES: MailCategory[] = [
  { id: "sales", name: "Sales", color: "violet" },
  { id: "customer", name: "Customer", color: "sky" },
  { id: "internal", name: "Internal", color: "emerald" },
  { id: "newsletter", name: "Newsletter", color: "amber" },
  { id: "vendor", name: "Vendor", color: "rose" },
  { id: "follow-up", name: "Follow-up", color: "fuchsia" },
];

export const CATEGORY_STYLES: Record<string, { dot: string; chip: string }> = {
  violet: { dot: "bg-violet-500", chip: "bg-violet-500/10 text-violet-600 dark:text-violet-400" },
  sky: { dot: "bg-sky-500", chip: "bg-sky-500/10 text-sky-600 dark:text-sky-400" },
  emerald: {
    dot: "bg-emerald-500",
    chip: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  },
  amber: { dot: "bg-amber-500", chip: "bg-amber-500/10 text-amber-600 dark:text-amber-400" },
  rose: { dot: "bg-rose-500", chip: "bg-rose-500/10 text-rose-600 dark:text-rose-400" },
  fuchsia: {
    dot: "bg-fuchsia-500",
    chip: "bg-fuchsia-500/10 text-fuchsia-600 dark:text-fuchsia-400",
  },
};

export function getCategory(id: string): MailCategory | undefined {
  return CATEGORIES.find((c) => c.id === id);
}
