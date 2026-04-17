import { createFileRoute, Link } from "@tanstack/react-router";
import { usePrefsStore } from "@/stores/ui-store";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bell, Palette, Keyboard, ExternalLink } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/settings/preferences")({
  component: PreferencesPage,
});

function PreferencesPage() {
  const prefs = usePrefsStore((s) => s.prefs);
  const patch = usePrefsStore((s) => s.patch);
  const setTheme = usePrefsStore((s) => s.setTheme);
  const setDensity = usePrefsStore((s) => s.setDensity);

  async function requestDesktopPermission() {
    if (typeof window === "undefined" || !("Notification" in window)) {
      toast.error("Desktop notifications are not supported in this browser");
      return;
    }
    const result = await Notification.requestPermission();
    if (result === "granted") {
      patch({ notifications: { ...prefs.notifications, desktop: true } });
      toast.success("Desktop notifications enabled");
    } else {
      toast("Permission denied — enable in browser settings");
    }
  }

  return (
    <ScrollArea className="h-full w-full">
      <div className="mx-auto max-w-3xl space-y-6 p-6">
        <header>
          <h1 className="text-2xl font-bold tracking-tight">Preferences</h1>
          <p className="text-sm text-muted-foreground">
            Personalize notifications, appearance and shortcuts across PSense.
          </p>
        </header>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Bell className="h-4 w-4" />
              </div>
              <div>
                <CardTitle>Notifications</CardTitle>
                <CardDescription>How and when you're alerted to new mail.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Row
              label="Desktop notifications"
              hint="Show a system notification when new mail arrives."
              value={prefs.notifications.desktop}
              onChange={(v) => {
                if (v) {
                  void requestDesktopPermission();
                } else {
                  patch({ notifications: { ...prefs.notifications, desktop: false } });
                }
              }}
            />
            <Row
              label="Notification sound"
              hint="Play a soft chime for incoming messages."
              value={prefs.notifications.sound}
              onChange={(v) =>
                patch({ notifications: { ...prefs.notifications, sound: v } })
              }
            />
            <Row
              label="Only Focused inbox"
              hint="Suppress alerts for messages routed to Other."
              value={prefs.notifications.onlyFocused}
              onChange={(v) =>
                patch({ notifications: { ...prefs.notifications, onlyFocused: v } })
              }
            />
            <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
              Email digest settings will move here when Lovable Cloud is connected.
            </div>
          </CardContent>
        </Card>

        {/* Appearance */}
        <Card>
          <CardHeader>
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Palette className="h-4 w-4" />
              </div>
              <div>
                <CardTitle>Appearance</CardTitle>
                <CardDescription>Theme, density and layout preferences.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Theme</Label>
                <Select
                  value={prefs.theme}
                  onValueChange={(v) => setTheme(v as typeof prefs.theme)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Light</SelectItem>
                    <SelectItem value="dark">Dark</SelectItem>
                    <SelectItem value="system">Match system</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Density</Label>
                <Select
                  value={prefs.density}
                  onValueChange={(v) => setDensity(v as typeof prefs.density)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="compact">Compact</SelectItem>
                    <SelectItem value="comfortable">Comfortable</SelectItem>
                    <SelectItem value="spacious">Spacious</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <ThemePreview theme={prefs.theme} />
          </CardContent>
        </Card>

        {/* Shortcuts */}
        <Card>
          <CardHeader>
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Keyboard className="h-4 w-4" />
              </div>
              <div>
                <CardTitle>Keyboard shortcuts</CardTitle>
                <CardDescription>Triage faster with single-key shortcuts.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Row
              label="Enable keyboard shortcuts"
              hint="Use j/k to move, e to archive, # to delete, and more."
              value={prefs.shortcutsEnabled}
              onChange={(v) => patch({ shortcutsEnabled: v })}
            />
            <div className="space-y-2 rounded-md border border-border bg-muted/30 p-3">
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Highlights
              </div>
              <div className="grid gap-1.5 text-sm sm:grid-cols-2">
                <ShortcutRow keys={["c"]} desc="Compose" />
                <ShortcutRow keys={["⌘", "K"]} desc="Command palette" />
                <ShortcutRow keys={["/"]} desc="Focus search" />
                <ShortcutRow keys={["?"]} desc="Show all shortcuts" />
                <ShortcutRow keys={["j"]} desc="Next message" />
                <ShortcutRow keys={["k"]} desc="Previous message" />
                <ShortcutRow keys={["e"]} desc="Archive" />
                <ShortcutRow keys={["#"]} desc="Delete" />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button asChild variant="outline" size="sm">
                <Link to="/settings/mail">
                  <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                  Mail-specific settings
                </Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link to="/settings/signatures">
                  <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                  Manage signatures
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  );
}

function Row({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <Label className="text-sm">{label}</Label>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      <Switch checked={value} onCheckedChange={onChange} />
    </div>
  );
}

function ShortcutRow({ keys, desc }: { keys: string[]; desc: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-muted-foreground">{desc}</span>
      <span className="flex items-center gap-1">
        {keys.map((k) => (
          <kbd
            key={k}
            className="inline-flex h-5 min-w-5 items-center justify-center rounded border border-border bg-background px-1.5 text-[11px] font-medium text-foreground shadow-sm"
          >
            {k}
          </kbd>
        ))}
      </span>
    </div>
  );
}

function ThemePreview({ theme }: { theme: "light" | "dark" | "system" }) {
  return (
    <div className="grid grid-cols-3 gap-2 pt-1">
      {(["light", "dark", "system"] as const).map((t) => (
        <div
          key={t}
          className={`overflow-hidden rounded-md border-2 ${
            theme === t ? "border-primary" : "border-border"
          }`}
        >
          <div
            className={`h-16 ${
              t === "light"
                ? "bg-white"
                : t === "dark"
                ? "bg-[#1a1024]"
                : "bg-gradient-to-r from-white to-[#1a1024]"
            } relative`}
          >
            <div className="absolute left-2 top-2 h-2 w-12 rounded-full bg-primary/60" />
            <div
              className={`absolute left-2 top-6 h-1.5 w-20 rounded-full ${
                t === "dark" ? "bg-white/30" : "bg-black/20"
              }`}
            />
            <div
              className={`absolute left-2 top-9 h-1.5 w-16 rounded-full ${
                t === "dark" ? "bg-white/20" : "bg-black/10"
              }`}
            />
          </div>
          <div className="bg-muted/40 px-2 py-1 text-center text-[11px] capitalize">
            {t}
          </div>
        </div>
      ))}
    </div>
  );
}
