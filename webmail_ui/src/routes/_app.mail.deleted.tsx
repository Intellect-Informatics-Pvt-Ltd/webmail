import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";

export const Route = createFileRoute("/_app/mail/deleted")({
  component: () => <MailWorkspace filter={{ folderKey: "deleted" }} title="Deleted items" />,
});
