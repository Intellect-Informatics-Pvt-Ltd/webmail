import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";

export const Route = createFileRoute("/_app/mail/flagged")({
  component: () => (
    <MailWorkspace filter={{ folderKey: "flagged" }} title="Flagged" description="Items you've flagged for follow-up" />
  ),
});
