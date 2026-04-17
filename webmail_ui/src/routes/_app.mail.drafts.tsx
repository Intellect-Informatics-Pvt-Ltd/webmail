import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";

export const Route = createFileRoute("/_app/mail/drafts")({
  component: () => (
    <MailWorkspace filter={{ folderKey: "drafts" }} title="Drafts" description="Saved drafts" />
  ),
});
