import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import Link from "@tiptap/extension-link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Strikethrough,
  List,
  ListOrdered,
  Quote,
  Link as LinkIcon,
  Undo2,
  Redo2,
  Paperclip,
  Send,
  Calendar as CalendarIcon,
  X,
  Maximize2,
  Minimize2,
  Minus,
  Save,
  Trash2,
  Type,
  AlignLeft,
  PenLine,
} from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { useComposeStore } from "@/stores/compose-store";
import { useMailStore } from "@/stores/mail-store";
import { isValidEmail } from "@/lib/mail-format";
import type { MailRecipient } from "@/types/mail";
import { toast } from "sonner";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function ComposeWindow() {
  const open = useComposeStore((s) => s.open);
  const update = useComposeStore((s) => s.updateOpen);
  const close = useComposeStore((s) => s.closeCompose);
  const save = useComposeStore((s) => s.saveDraft);
  const discard = useComposeStore((s) => s.discardDraft);
  const toggleExpanded = useComposeStore((s) => s.toggleExpanded);
  const toggleMinimized = useComposeStore((s) => s.toggleMinimized);
  const upsertMessage = useMailStore((s) => s.upsertMessage);
  const templates = useMailStore((s) => s.templates);
  const signatures = useMailStore((s) => s.signatures);

  const editor = useEditor(
    {
      immediatelyRender: false,
      extensions: [
        StarterKit.configure({}),
        Placeholder.configure({ placeholder: "Write your message…" }),
        Link.configure({ openOnClick: false }),
      ],
      content: open?.bodyHtml ?? "",
      editorProps: {
        attributes: {
          class: "ProseMirror prose prose-sm max-w-none p-4 focus:outline-none",
        },
      },
      onUpdate: ({ editor }) => update({ bodyHtml: editor.getHTML() }),
    },
    [open?.id],
  );

  // autosave every 5s when dirty
  const dirtyRef = useRef(false);
  useEffect(() => {
    if (!open) return;
    dirtyRef.current = true;
    const t = setInterval(() => {
      if (dirtyRef.current) {
        save();
        dirtyRef.current = false;
      }
    }, 5000);
    return () => clearInterval(t);
  }, [open?.id, open?.subject, open?.bodyHtml, save, open]);

  // Auto-append the default signature to a brand-new draft once.
  // Re-runs when the user toggles signatureDisabled so they can add/remove it inline.
  const sigAppliedRef = useRef<string | null>(null);
  useEffect(() => {
    if (!open || !editor) return;
    const defaultSig = signatures.find((s) => s.isDefault);
    if (!defaultSig) return;
    const sigBlock = `<div data-signature="default">${defaultSig.bodyHtml}</div>`;
    const current = editor.getHTML();
    const hasSig = current.includes('data-signature="default"');

    if (!open.signatureDisabled && !hasSig) {
      // Only auto-append on a draft whose body is effectively empty (no user content yet)
      const stripped = current.replace(/<[^>]+>/g, "").trim();
      if (stripped.length === 0 && sigAppliedRef.current !== open.id) {
        const next = `<p></p>${sigBlock}`;
        editor.commands.setContent(next, { emitUpdate: false });
        update({ bodyHtml: next });
        sigAppliedRef.current = open.id;
      }
    } else if (open.signatureDisabled && hasSig) {
      const next = current.replace(
        /<div data-signature="default">[\s\S]*?<\/div>/g,
        "",
      );
      editor.commands.setContent(next, { emitUpdate: false });
      update({ bodyHtml: next });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open?.id, open?.signatureDisabled, editor, signatures]);


  // Keyboard shortcuts: ⌘/Ctrl+Enter to send, Esc to minimize, ⌘/Ctrl+Shift+M to toggle minimize
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key === "Enter") {
        e.preventDefault();
        handleSend();
      } else if (mod && e.shiftKey && (e.key === "m" || e.key === "M")) {
        e.preventDefault();
        toggleMinimized();
      } else if (e.key === "Escape" && !open.minimized) {
        // Don't hijack Esc when other overlays/menus are open
        const hasOpenOverlay = document.querySelector(
          "[data-state='open'][role='dialog'], [data-state='open'][role='menu']",
        );
        if (!hasOpenOverlay) {
          e.preventDefault();
          toggleMinimized();
        }
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) return null;

  function handleSend() {
    if (!open) return;
    if (open.to.length === 0) {
      toast.error("Add at least one recipient");
      return;
    }
    upsertMessage({
      id: `s-${Date.now()}`,
      threadId: open.inReplyToId ?? `t-${Date.now()}`,
      folderId: "sent",
      subject: open.subject || "(no subject)",
      preview: open.bodyHtml.replace(/<[^>]+>/g, "").slice(0, 140),
      bodyHtml: open.bodyHtml,
      sender: { name: "Avery Chen", email: "avery@psense.ai" },
      recipients: open.to,
      cc: open.cc,
      bcc: open.bcc,
      receivedAt: new Date().toISOString(),
      isRead: true,
      isFlagged: false,
      isPinned: false,
      hasAttachments: open.attachments.length > 0,
      importance: "normal",
      categories: [],
      attachments: open.attachments,
    });
    toast.success("Message sent");
    discard(open.id);
  }

  if (open.minimized) {
    return (
      <div
        className="fixed bottom-0 right-6 z-50 flex h-10 w-72 items-center gap-2 rounded-t-lg border border-b-0 border-border bg-card px-3 shadow-2xl"
        role="dialog"
        aria-label="Minimized compose"
      >
        <button
          type="button"
          className="flex-1 truncate text-left text-sm font-medium hover:text-primary"
          onClick={toggleMinimized}
          title="Restore"
        >
          {open.subject || "New message"}
        </button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label="Restore"
          onClick={toggleMinimized}
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label="Close"
          onClick={() => {
            save();
            close();
            toast("Draft saved");
          }}
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "fixed z-50 flex flex-col overflow-hidden rounded-lg border border-border bg-card shadow-2xl",
        open.expanded
          ? "inset-4 md:inset-10"
          : "bottom-12 right-6 h-[560px] w-[560px] max-w-[calc(100vw-3rem)]",
      )}
      role="dialog"
      aria-label="Compose message"
    >
      {/* Title bar */}
      <div className="flex h-10 shrink-0 items-center gap-2 border-b border-border bg-muted/40 px-3">
        <span className="truncate text-sm font-medium">
          {open.subject || "New message"}
        </span>
        <div className="ml-auto flex items-center gap-1">
          {open.lastSavedAt && (
            <span className="mr-2 text-[11px] text-muted-foreground">Draft saved</span>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="Minimize"
            onClick={toggleMinimized}
          >
            <Minus className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label={open.expanded ? "Restore" : "Expand"}
            onClick={toggleExpanded}
          >
            {open.expanded ? (
              <Minimize2 className="h-3.5 w-3.5" />
            ) : (
              <Maximize2 className="h-3.5 w-3.5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="Close"
            onClick={() => {
              save();
              close();
              toast("Draft saved");
            }}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Recipient fields */}
      <div className="space-y-1 border-b border-border px-3 py-2">
        <RecipientRow
          label="To"
          recipients={open.to}
          onChange={(to) => update({ to })}
          aside={
            <div className="flex gap-2 text-xs text-muted-foreground">
              {!open.showCc && (
                <button type="button" className="hover:text-foreground" onClick={() => update({ showCc: true })}>
                  Cc
                </button>
              )}
              {!open.showBcc && (
                <button type="button" className="hover:text-foreground" onClick={() => update({ showBcc: true })}>
                  Bcc
                </button>
              )}
            </div>
          }
        />
        {open.showCc && (
          <RecipientRow label="Cc" recipients={open.cc} onChange={(cc) => update({ cc })} />
        )}
        {open.showBcc && (
          <RecipientRow label="Bcc" recipients={open.bcc} onChange={(bcc) => update({ bcc })} />
        )}
        <div className="flex items-center gap-2 pt-1">
          <span className="w-12 shrink-0 text-xs font-medium text-muted-foreground">Subject</span>
          <Input
            value={open.subject}
            onChange={(e) => update({ subject: e.target.value })}
            placeholder="Subject"
            className="h-8 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
          />
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex h-10 shrink-0 items-center gap-0.5 border-b border-border bg-background px-2">
        <FmtBtn label="Bold" active={editor?.isActive("bold")} onClick={() => editor?.chain().focus().toggleBold().run()}>
          <Bold className="h-3.5 w-3.5" />
        </FmtBtn>
        <FmtBtn label="Italic" active={editor?.isActive("italic")} onClick={() => editor?.chain().focus().toggleItalic().run()}>
          <Italic className="h-3.5 w-3.5" />
        </FmtBtn>
        <FmtBtn label="Underline" onClick={() => editor?.chain().focus().toggleMark("underline" as never).run()}>
          <UnderlineIcon className="h-3.5 w-3.5" />
        </FmtBtn>
        <FmtBtn label="Strike" active={editor?.isActive("strike")} onClick={() => editor?.chain().focus().toggleStrike().run()}>
          <Strikethrough className="h-3.5 w-3.5" />
        </FmtBtn>
        <Separator orientation="vertical" className="mx-1 h-5" />
        <FmtBtn label="Bulleted list" active={editor?.isActive("bulletList")} onClick={() => editor?.chain().focus().toggleBulletList().run()}>
          <List className="h-3.5 w-3.5" />
        </FmtBtn>
        <FmtBtn label="Numbered list" active={editor?.isActive("orderedList")} onClick={() => editor?.chain().focus().toggleOrderedList().run()}>
          <ListOrdered className="h-3.5 w-3.5" />
        </FmtBtn>
        <FmtBtn label="Quote" active={editor?.isActive("blockquote")} onClick={() => editor?.chain().focus().toggleBlockquote().run()}>
          <Quote className="h-3.5 w-3.5" />
        </FmtBtn>
        <FmtBtn
          label="Link"
          onClick={() => {
            const url = window.prompt("Link URL");
            if (url) editor?.chain().focus().setLink({ href: url }).run();
          }}
        >
          <LinkIcon className="h-3.5 w-3.5" />
        </FmtBtn>
        <Separator orientation="vertical" className="mx-1 h-5" />
        <FmtBtn label="Undo" onClick={() => editor?.chain().focus().undo().run()}>
          <Undo2 className="h-3.5 w-3.5" />
        </FmtBtn>
        <FmtBtn label="Redo" onClick={() => editor?.chain().focus().redo().run()}>
          <Redo2 className="h-3.5 w-3.5" />
        </FmtBtn>
        <Separator orientation="vertical" className="mx-1 h-5" />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs">
              <Type className="h-3.5 w-3.5" /> Template
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {templates.map((t) => (
              <DropdownMenuItem
                key={t.id}
                onClick={() => {
                  update({ subject: open.subject || t.subject, bodyHtml: t.bodyHtml });
                  editor?.commands.setContent(t.bodyHtml);
                }}
              >
                {t.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs">
              <AlignLeft className="h-3.5 w-3.5" /> Signature
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            {signatures.map((s) => (
              <DropdownMenuItem
                key={s.id}
                onClick={() => {
                  const next = `${editor?.getHTML() ?? ""}<br/>${s.bodyHtml}`;
                  editor?.commands.setContent(next);
                  update({ bodyHtml: next });
                }}
              >
                {s.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="ghost"
          size="sm"
          className="h-7 gap-1 px-2 text-xs"
          onClick={() => toast("Attachments are placeholders in this demo")}
        >
          <Paperclip className="h-3.5 w-3.5" /> Attach
        </Button>
      </div>

      {/* Editor */}
      <div className="flex-1 overflow-auto bg-card">
        <EditorContent editor={editor} />
      </div>

      {/* Footer actions */}
      <div className="flex h-12 shrink-0 items-center gap-2 border-t border-border bg-muted/30 px-3">
        <Button onClick={handleSend} className="h-8 gap-1.5">
          <Send className="h-3.5 w-3.5" /> Send
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-8 gap-1"
          onClick={() => {
            update({ scheduledFor: new Date(Date.now() + 24 * 3600_000).toISOString() });
            save();
            toast.success("Scheduled for tomorrow");
            close();
          }}
        >
          <CalendarIcon className="h-3.5 w-3.5" /> Schedule
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 gap-1"
          onClick={() => {
            save();
            toast("Draft saved");
          }}
        >
          <Save className="h-3.5 w-3.5" /> Save draft
        </Button>

        {signatures.some((s) => s.isDefault) && (
          <div
            className="ml-auto flex items-center gap-1.5 rounded-md border border-border bg-background px-2 py-1"
            title="Auto-append your default signature"
          >
            <PenLine className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
            <Label htmlFor="sig-toggle" className="text-xs text-muted-foreground">
              Signature
            </Label>
            <Switch
              id="sig-toggle"
              checked={!open.signatureDisabled}
              onCheckedChange={(v) => update({ signatureDisabled: !v })}
              aria-label="Toggle default signature"
            />
          </div>
        )}

        <Button
          variant="ghost"
          size="sm"
          className={cn(
            "h-8 gap-1 text-muted-foreground hover:text-destructive",
            !signatures.some((s) => s.isDefault) && "ml-auto",
          )}
          onClick={() => {
            discard();
            toast("Draft discarded");
          }}
        >
          <Trash2 className="h-3.5 w-3.5" /> Discard
        </Button>
      </div>
    </div>
  );
}

function FmtBtn({
  label,
  active,
  onClick,
  children,
}: {
  label: string;
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className={cn(
        "inline-flex h-7 w-7 items-center justify-center rounded text-foreground/80 hover:bg-muted",
        active && "bg-muted text-foreground",
      )}
    >
      {children}
    </button>
  );
}

function RecipientRow({
  label,
  recipients,
  onChange,
  aside,
}: {
  label: string;
  recipients: MailRecipient[];
  onChange: (next: MailRecipient[]) => void;
  aside?: React.ReactNode;
}) {
  const [draft, setDraft] = useState("");
  const invalid = useMemo(() => recipients.filter((r) => !isValidEmail(r.email)), [recipients]);

  function commit(s: string) {
    const v = s.trim().replace(/[,;]$/, "");
    if (!v) return;
    onChange([...recipients, { name: v.split("@")[0], email: v }]);
    setDraft("");
  }

  return (
    <div className="flex items-start gap-2">
      <span className="w-12 shrink-0 pt-1.5 text-xs font-medium text-muted-foreground">{label}</span>
      <div className="flex flex-1 flex-wrap items-center gap-1">
        {recipients.map((r, i) => {
          const isInvalid = invalid.includes(r);
          return (
            <span
              key={`${r.email}-${i}`}
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs",
                isInvalid
                  ? "bg-destructive/10 text-destructive ring-1 ring-destructive/30"
                  : "bg-secondary text-secondary-foreground",
              )}
            >
              {r.email}
              <button
                type="button"
                aria-label={`Remove ${r.email}`}
                className="opacity-60 hover:opacity-100"
                onClick={() => onChange(recipients.filter((_, j) => j !== i))}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          );
        })}
        <input
          value={draft}
          onChange={(e) => {
            const v = e.target.value;
            if (v.endsWith(",") || v.endsWith(";")) commit(v.slice(0, -1));
            else setDraft(v);
          }}
          onBlur={() => commit(draft)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === "Tab") {
              e.preventDefault();
              commit(draft);
            } else if (e.key === "Backspace" && !draft && recipients.length > 0) {
              onChange(recipients.slice(0, -1));
            }
          }}
          placeholder={recipients.length === 0 ? "name@example.com" : ""}
          className="min-w-[120px] flex-1 bg-transparent py-1 text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>
      {aside}
    </div>
  );
}
