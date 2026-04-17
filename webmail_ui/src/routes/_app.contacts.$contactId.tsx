import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Mail, Phone, Building2, Pin, Trash2, ArrowLeft } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { initialsOf, avatarColorFor } from "@/lib/mail-format";
import { useContactsStore } from "@/stores/contacts-store";
import { useComposeStore } from "@/stores/compose-store";
import { CONTACT_GROUPS } from "@/data/contacts";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/contacts/$contactId")({
  component: ContactDetail,
});

function ContactDetail() {
  const { contactId } = Route.useParams();
  const navigate = useNavigate();
  const contacts = useContactsStore((s) => s.contacts);
  const togglePinned = useContactsStore((s) => s.togglePinned);
  const deleteContact = useContactsStore((s) => s.deleteContact);
  const openCompose = useComposeStore((s) => s.openCompose);

  const contact = contacts.find((c) => c.id === contactId);
  if (!contact) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <h2 className="text-lg font-semibold">Contact not found</h2>
        <p className="text-sm text-muted-foreground">This contact may have been deleted.</p>
        <Button asChild variant="outline" size="sm">
          <Link to="/contacts">Back to contacts</Link>
        </Button>
      </div>
    );
  }

  const groupLabel = CONTACT_GROUPS.find((g) => g.id === contact.group)?.label;

  return (
    <article className="flex h-full flex-col overflow-y-auto">
      <header className="flex items-start gap-4 border-b border-border p-6">
        <Button
          asChild
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label="Back"
        >
          <Link to="/contacts">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <Avatar className="h-16 w-16">
          <AvatarFallback
            className={`${avatarColorFor(contact.email)} text-lg font-semibold text-white`}
          >
            {initialsOf(contact.name)}
          </AvatarFallback>
        </Avatar>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h1 className="truncate text-xl font-semibold tracking-tight">{contact.name}</h1>
          {contact.role && (
            <p className="truncate text-sm text-muted-foreground">
              {contact.role}
              {contact.company ? ` · ${contact.company}` : ""}
            </p>
          )}
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {groupLabel && (
              <Badge variant="secondary" className="text-xs">
                {groupLabel}
              </Badge>
            )}
            {contact.pinned && (
              <Badge variant="outline" className="gap-1 text-xs">
                <Pin className="h-3 w-3" /> Pinned
              </Badge>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            size="sm"
            className="gap-1.5"
            onClick={() => {
              openCompose({
                to: [{ name: contact.name, email: contact.email }],
              });
              toast.success(`New message to ${contact.name}`);
            }}
          >
            <Mail className="h-4 w-4" /> Email
          </Button>
        </div>
      </header>

      <div className="space-y-6 p-6">
        <section>
          <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Contact info
          </h2>
          <div className="space-y-2 rounded-lg border border-border bg-card p-4">
            <DetailRow icon={<Mail className="h-4 w-4" />} label="Email">
              <a
                href={`mailto:${contact.email}`}
                onClick={(e) => {
                  e.preventDefault();
                  openCompose({
                    to: [{ name: contact.name, email: contact.email }],
                  });
                }}
                className="text-sm text-primary hover:underline"
              >
                {contact.email}
              </a>
            </DetailRow>
            {contact.phone && (
              <>
                <Separator />
                <DetailRow icon={<Phone className="h-4 w-4" />} label="Phone">
                  <span className="text-sm">{contact.phone}</span>
                </DetailRow>
              </>
            )}
            {contact.company && (
              <>
                <Separator />
                <DetailRow icon={<Building2 className="h-4 w-4" />} label="Company">
                  <span className="text-sm">{contact.company}</span>
                </DetailRow>
              </>
            )}
          </div>
        </section>

        {contact.notes && (
          <section>
            <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Notes
            </h2>
            <p className="rounded-lg border border-border bg-card p-4 text-sm leading-relaxed text-foreground/80">
              {contact.notes}
            </p>
          </section>
        )}

        <section className="flex flex-wrap items-center gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => {
              togglePinned(contact.id);
              toast(contact.pinned ? "Unpinned" : "Pinned to top");
            }}
          >
            <Pin className="h-4 w-4" />
            {contact.pinned ? "Unpin" : "Pin"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto gap-1.5 text-muted-foreground hover:text-destructive"
            onClick={() => {
              deleteContact(contact.id);
              toast(`Deleted ${contact.name}`);
              navigate({ to: "/contacts" });
            }}
          >
            <Trash2 className="h-4 w-4" /> Delete
          </Button>
        </section>
      </div>
    </article>
  );
}

function DetailRow({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <div className="truncate">{children}</div>
      </div>
    </div>
  );
}
