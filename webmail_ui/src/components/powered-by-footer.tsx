import { PsenseLogo } from "@/components/psense-logo";

export function PoweredByFooter() {
  return (
    <footer className="flex h-8 items-center justify-end border-t border-border bg-background px-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span>Powered by</span>
        <PsenseLogo className="h-3.5 w-auto opacity-80" />
      </div>
    </footer>
  );
}
