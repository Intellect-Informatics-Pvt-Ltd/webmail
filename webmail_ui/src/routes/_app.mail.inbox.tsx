import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";

export const Route = createFileRoute("/_app/mail/inbox")({
  component: () => (
    <MailWorkspace
      filter={{ folderKey: "inbox" }}
      title="Inbox"
      description="All incoming mail"
    />
  ),
});
