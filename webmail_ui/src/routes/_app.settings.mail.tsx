import { createFileRoute } from "@tanstack/react-router";
import { usePrefsStore } from "@/stores/ui-store";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";

export const Route = createFileRoute("/_app/settings/mail")({
  component: MailSettings,
});

function MailSettings() {
  const prefs = usePrefsStore((s) => s.prefs);
  const patch = usePrefsStore((s) => s.patch);
  const setDensity = usePrefsStore((s) => s.setDensity);
  const setReadingPane = usePrefsStore((s) => s.setReadingPane);
  const setTheme = usePrefsStore((s) => s.setTheme);

  return (
    <ScrollArea className="h-full w-full">
      <div className="mx-auto max-w-3xl space-y-6 p-6">
        <header>
          <h1 className="text-2xl font-bold tracking-tight">Mail settings</h1>
          <p className="text-sm text-muted-foreground">Tune how mail looks and behaves.</p>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>Layout & density</CardTitle>
            <CardDescription>Reading pane, density and theme.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Reading pane</Label>
              <Select
                value={prefs.readingPane}
                onValueChange={(v) => setReadingPane(v as typeof prefs.readingPane)}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="right">Right</SelectItem>
                  <SelectItem value="bottom">Bottom</SelectItem>
                  <SelectItem value="off">Off</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Density</Label>
              <Select value={prefs.density} onValueChange={(v) => setDensity(v as typeof prefs.density)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="compact">Compact</SelectItem>
                  <SelectItem value="comfortable">Comfortable</SelectItem>
                  <SelectItem value="spacious">Spacious</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Theme</Label>
              <Select value={prefs.theme} onValueChange={(v) => setTheme(v as typeof prefs.theme)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="dark">Dark</SelectItem>
                  <SelectItem value="system">System</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Preview lines</Label>
              <Select
                value={String(prefs.previewLines)}
                onValueChange={(v) => patch({ previewLines: Number(v) as 1 | 2 | 3 })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 line</SelectItem>
                  <SelectItem value="2">2 lines</SelectItem>
                  <SelectItem value="3">3 lines</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Inbox behavior</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Toggle
              label="Conversation view"
              hint="Group related messages into threads."
              value={prefs.conversationView}
              onChange={(v) => patch({ conversationView: v })}
            />
            <Toggle
              label="Focused inbox"
              hint="Split your inbox into Focused and Other."
              value={prefs.focusedInbox}
              onChange={(v) => patch({ focusedInbox: v })}
            />
            <Toggle
              label="Keyboard shortcuts"
              hint="Use j/k, e, #, u, f for fast triage."
              value={prefs.shortcutsEnabled}
              onChange={(v) => patch({ shortcutsEnabled: v })}
            />
            <div className="space-y-2">
              <Label>Default reply</Label>
              <Select
                value={prefs.defaultReply}
                onValueChange={(v) => patch({ defaultReply: v as typeof prefs.defaultReply })}
              >
                <SelectTrigger className="max-w-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="reply">Reply</SelectItem>
                  <SelectItem value="replyAll">Reply all</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Toggle
              label="Desktop notifications"
              value={prefs.notifications.desktop}
              onChange={(v) =>
                patch({ notifications: { ...prefs.notifications, desktop: v } })
              }
            />
            <Toggle
              label="Sound"
              value={prefs.notifications.sound}
              onChange={(v) =>
                patch({ notifications: { ...prefs.notifications, sound: v } })
              }
            />
            <Toggle
              label="Only Focused inbox"
              value={prefs.notifications.onlyFocused}
              onChange={(v) =>
                patch({ notifications: { ...prefs.notifications, onlyFocused: v } })
              }
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Out of office</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Toggle
              label="Send automatic replies"
              value={prefs.outOfOffice.enabled}
              onChange={(v) => patch({ outOfOffice: { ...prefs.outOfOffice, enabled: v } })}
            />
            <Textarea
              placeholder="I'm currently out of office and will reply when I return..."
              value={prefs.outOfOffice.message}
              onChange={(e) =>
                patch({ outOfOffice: { ...prefs.outOfOffice, message: e.target.value } })
              }
              rows={4}
            />
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  );
}

function Toggle({
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
      <div>
        <Label className="text-sm">{label}</Label>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      <Switch checked={value} onCheckedChange={onChange} />
    </div>
  );
}
