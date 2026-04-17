import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";

export const Route = createFileRoute("/_app/mail/focused")({
  component: () => (
    <MailWorkspace
      filter={{ folderKey: "focused" }}
      title="Focused"
      description="Your most important conversations"
    />
  ),
});
