import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";

export const Route = createFileRoute("/_app/mail/sent")({
  component: () => <MailWorkspace filter={{ folderKey: "sent" }} title="Sent" />,
});
