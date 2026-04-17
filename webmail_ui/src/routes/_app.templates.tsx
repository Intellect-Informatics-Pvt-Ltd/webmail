import { createFileRoute } from "@tanstack/react-router";
import { useMailStore } from "@/stores/mail-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, Trash2, FileText } from "lucide-react";
import { useComposeStore } from "@/stores/compose-store";

export const Route = createFileRoute("/_app/templates")({
  component: TemplatesPage,
});

function TemplatesPage() {
  const templates = useMailStore((s) => s.templates);
  const deleteTemplate = useMailStore((s) => s.deleteTemplate);
  const addTemplate = useMailStore((s) => s.addTemplate);
  const openCompose = useComposeStore((s) => s.openCompose);

  return (
    <ScrollArea className="h-full w-full">
      <div className="mx-auto max-w-4xl space-y-6 p-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Templates</h1>
            <p className="text-sm text-muted-foreground">
              Reusable message templates for fast replies.
            </p>
          </div>
          <Button
            onClick={() =>
              addTemplate({
                id: `tpl-${Date.now()}`,
                name: "Untitled template",
                subject: "",
                bodyHtml: "<p></p>",
              })
            }
          >
            <Plus className="mr-2 h-4 w-4" /> New template
          </Button>
        </header>

        <div className="grid gap-3">
          {templates.map((t) => (
            <Card key={t.id}>
              <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{t.name}</CardTitle>
                    <p className="mt-0.5 text-xs text-muted-foreground">{t.subject || "(no subject)"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      openCompose({ subject: t.subject, bodyHtml: t.bodyHtml })
                    }
                  >
                    Use template
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Delete"
                    onClick={() => deleteTemplate(t.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div
                  className="prose prose-sm max-w-none text-xs text-muted-foreground"
                  dangerouslySetInnerHTML={{ __html: t.bodyHtml }}
                />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </ScrollArea>
  );
}
