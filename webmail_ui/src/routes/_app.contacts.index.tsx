import { createFileRoute } from "@tanstack/react-router";
import { Users } from "lucide-react";

export const Route = createFileRoute("/_app/contacts/")({
  component: ContactsIndex,
});

function ContactsIndex() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Users className="h-7 w-7" aria-hidden />
      </div>
      <div>
        <h2 className="text-lg font-semibold">Select a contact</h2>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          Choose someone from the list to see their details, or use the search to find a person fast.
        </p>
      </div>
    </div>
  );
}
