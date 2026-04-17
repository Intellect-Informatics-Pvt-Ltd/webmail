import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";

export const Route = createFileRoute("/_app/mail/archive")({
  component: () => <MailWorkspace filter={{ folderKey: "archive" }} title="Archive" />,
});
