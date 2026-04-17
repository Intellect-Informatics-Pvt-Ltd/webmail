import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";

export const Route = createFileRoute("/_app/mail/other")({
  component: () => (
    <MailWorkspace filter={{ folderKey: "other" }} title="Other" description="Everything else" />
  ),
});
