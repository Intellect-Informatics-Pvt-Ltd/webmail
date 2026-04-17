import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";

export const Route = createFileRoute("/_app/mail/junk")({
  component: () => <MailWorkspace filter={{ folderKey: "junk" }} title="Junk" />,
});
