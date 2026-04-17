import { Outlet, createFileRoute } from "@tanstack/react-router";
import { ContactsSidebar } from "@/components/contacts/contacts-sidebar";
import { ContactsList } from "@/components/contacts/contacts-list";

export const Route = createFileRoute("/_app/contacts")({
  component: ContactsLayout,
});

function ContactsLayout() {
  return (
    <div className="flex h-full w-full flex-1 overflow-hidden bg-background">
      <ContactsSidebar />
      <ContactsList />
      <div className="flex-1 overflow-hidden border-l border-border">
        <Outlet />
      </div>
    </div>
  );
}
