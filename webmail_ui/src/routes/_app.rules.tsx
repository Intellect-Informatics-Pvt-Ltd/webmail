import { createFileRoute } from "@tanstack/react-router";
import { useMailStore } from "@/stores/mail-store";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, Trash2, Wand2 } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/rules")({
  component: RulesPage,
});

function RulesPage() {
  const rules = useMailStore((s) => s.rules);
  const updateRule = useMailStore((s) => s.updateRule);
  const deleteRule = useMailStore((s) => s.deleteRule);
  const addRule = useMailStore((s) => s.addRule);

  return (
    <ScrollArea className="h-full w-full">
      <div className="mx-auto max-w-4xl space-y-6 p-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Rules</h1>
            <p className="text-sm text-muted-foreground">
              Automate your inbox — sort, categorize, and prioritize incoming mail.
            </p>
          </div>
          <Button
            onClick={() => {
              addRule({
                id: `r-${Date.now()}`,
                name: "Untitled rule",
                enabled: true,
                conditions: [{ field: "sender", op: "contains", value: "" }],
                actions: [{ type: "markImportant" }],
              });
              toast.success("Rule created");
            }}
          >
            <Plus className="mr-2 h-4 w-4" /> New rule
          </Button>
        </header>

        {rules.length === 0 ? (
          <EmptyRules />
        ) : (
          <div className="grid gap-3">
            {rules.map((r) => (
              <Card key={r.id}>
                <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
                  <div>
                    <CardTitle className="text-base">{r.name}</CardTitle>
                    <CardDescription className="mt-1 text-xs">
                      {r.conditions
                        .map((c) =>
                          c.field === "sender"
                            ? `Sender contains "${c.value}"`
                            : c.field === "subject"
                              ? `Subject contains "${c.value}"`
                              : c.field === "hasAttachment"
                                ? "Has attachment"
                                : `Older than ${c.value} days`,
                        )
                        .join(" · ")}
                      {" → "}
                      {r.actions
                        .map((a) =>
                          a.type === "move"
                            ? `Move to ${a.folderId}`
                            : a.type === "categorize"
                              ? `Categorize as ${a.categoryId}`
                              : a.type === "markImportant"
                                ? "Mark important"
                                : a.type,
                        )
                        .join(", ")}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={r.enabled}
                      onCheckedChange={(v) => updateRule({ ...r, enabled: v })}
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Delete rule"
                      onClick={() => deleteRule(r.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground">
                  Status: {r.enabled ? "Enabled" : "Disabled"}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </ScrollArea>
  );
}

function EmptyRules() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border p-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
        <Wand2 className="h-5 w-5 text-primary" />
      </div>
      <div>
        <p className="text-sm font-medium">No rules yet</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Rules automatically organize incoming mail. Create your first one above.
        </p>
      </div>
    </div>
  );
}
