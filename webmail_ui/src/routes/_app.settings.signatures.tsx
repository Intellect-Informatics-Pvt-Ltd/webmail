import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMailStore } from "@/stores/mail-store";
import { useComposeStore } from "@/stores/compose-store";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Plus, Trash2, Edit3, Star, Mail, PenSquare } from "lucide-react";
import { toast } from "sonner";
import type { MailSignature } from "@/types/mail";

export const Route = createFileRoute("/_app/settings/signatures")({
  component: SignaturesPage,
});

function SignaturesPage() {
  const signatures = useMailStore((s) => s.signatures);
  const setSignatures = useMailStore.setState;
  const openCompose = useComposeStore((s) => s.openCompose);

  const [editing, setEditing] = useState<MailSignature | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  function persist(next: MailSignature[]) {
    setSignatures({ signatures: next });
  }

  function startNew() {
    setEditing({
      id: `sig-${Date.now()}`,
      name: "Untitled signature",
      bodyHtml: "<p>Best,<br/>Your name<br/><em>Your title · PSense.ai</em></p>",
      isDefault: signatures.length === 0,
    });
    setEditorOpen(true);
  }

  function startEdit(sig: MailSignature) {
    setEditing({ ...sig });
    setEditorOpen(true);
  }

  function save() {
    if (!editing) return;
    const trimmed = editing.name.trim();
    if (!trimmed) {
      toast.error("Signature needs a name");
      return;
    }
    const next: MailSignature = { ...editing, name: trimmed };
    const exists = signatures.some((s) => s.id === next.id);
    let updated = exists
      ? signatures.map((s) => (s.id === next.id ? next : s))
      : [next, ...signatures];
    if (next.isDefault) {
      updated = updated.map((s) => ({ ...s, isDefault: s.id === next.id }));
    }
    persist(updated);
    setEditorOpen(false);
    setEditing(null);
    toast.success(exists ? "Signature updated" : "Signature created");
  }

  function setDefault(id: string) {
    persist(signatures.map((s) => ({ ...s, isDefault: s.id === id })));
    toast.success("Default signature updated");
  }

  function remove(id: string) {
    const removed = signatures.find((s) => s.id === id);
    persist(signatures.filter((s) => s.id !== id));
    setConfirmDelete(null);
    toast(`Deleted "${removed?.name ?? "signature"}"`);
  }

  function insertInCompose(sig: MailSignature) {
    openCompose({ bodyHtml: `<p></p><br/>${sig.bodyHtml}` });
    toast.success(`Inserted "${sig.name}" into a new draft`);
  }

  return (
    <ScrollArea className="h-full w-full">
      <div className="mx-auto max-w-4xl space-y-6 p-6">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Signatures</h1>
            <p className="text-sm text-muted-foreground">
              Create reusable sign-offs and pick a default for new messages.
            </p>
          </div>
          <Button onClick={startNew}>
            <Plus className="mr-2 h-4 w-4" /> New signature
          </Button>
        </header>

        {signatures.length === 0 ? (
          <EmptyState onCreate={startNew} />
        ) : (
          <div className="grid gap-3">
            {signatures.map((sig) => (
              <Card key={sig.id}>
                <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                      <Mail className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <CardTitle className="truncate text-base">{sig.name}</CardTitle>
                        {sig.isDefault && (
                          <Badge variant="secondary" className="gap-1">
                            <Star className="h-3 w-3 fill-current" /> Default
                          </Badge>
                        )}
                      </div>
                      <CardDescription className="text-xs">
                        Used when composing new mail
                      </CardDescription>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    {!sig.isDefault && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDefault(sig.id)}
                      >
                        <Star className="mr-1.5 h-3.5 w-3.5" /> Make default
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => insertInCompose(sig)}
                    >
                      <PenSquare className="mr-1.5 h-3.5 w-3.5" /> Insert
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Edit"
                      onClick={() => startEdit(sig)}
                    >
                      <Edit3 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Delete"
                      onClick={() => setConfirmDelete(sig.id)}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div
                    className="prose prose-sm max-w-none rounded-md border border-border bg-muted/30 p-3 text-sm text-foreground/80"
                    dangerouslySetInnerHTML={{ __html: sig.bodyHtml }}
                  />
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Editor dialog */}
      <Dialog open={editorOpen} onOpenChange={setEditorOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editing && signatures.some((s) => s.id === editing.id)
                ? "Edit signature"
                : "New signature"}
            </DialogTitle>
            <DialogDescription>
              HTML is allowed — keep formatting simple for the best deliverability.
            </DialogDescription>
          </DialogHeader>
          {editing && (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="sig-name">Name</Label>
                <Input
                  id="sig-name"
                  value={editing.name}
                  onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                  placeholder="e.g. Work, Personal, Sales outreach"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sig-body">Content (HTML)</Label>
                <Textarea
                  id="sig-body"
                  rows={8}
                  className="font-mono text-xs"
                  value={editing.bodyHtml}
                  onChange={(e) =>
                    setEditing({ ...editing, bodyHtml: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs uppercase tracking-wide text-muted-foreground">
                  Preview
                </Label>
                <div
                  className="prose prose-sm max-w-none rounded-md border border-border bg-muted/30 p-3"
                  dangerouslySetInnerHTML={{ __html: editing.bodyHtml }}
                />
              </div>
              <div className="flex items-center justify-between rounded-md border border-border p-3">
                <div>
                  <Label className="text-sm">Set as default</Label>
                  <p className="text-xs text-muted-foreground">
                    Inserted automatically into new compose windows.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={!!editing.isDefault}
                  onChange={(e) =>
                    setEditing({ ...editing, isDefault: e.target.checked })
                  }
                  className="h-4 w-4 accent-primary"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditorOpen(false)}>
              Cancel
            </Button>
            <Button onClick={save}>Save signature</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm delete */}
      <AlertDialog
        open={!!confirmDelete}
        onOpenChange={(o) => !o && setConfirmDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this signature?</AlertDialogTitle>
            <AlertDialogDescription>
              This can't be undone. Drafts that already used it will keep the inserted
              content.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => confirmDelete && remove(confirmDelete)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </ScrollArea>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Mail className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-base font-semibold">No signatures yet</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Create one to sign off your messages with style.
          </p>
        </div>
        <Button onClick={onCreate}>
          <Plus className="mr-2 h-4 w-4" /> Create signature
        </Button>
      </CardContent>
    </Card>
  );
}
