import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";
import { useMailStore } from "@/stores/mail-store";

export const Route = createFileRoute("/_app/mail/folder/$folderId")({
  component: FolderView,
});

function FolderView() {
  const { folderId } = Route.useParams();
  const folder = useMailStore((s) => s.customFolders.find((f) => f.id === folderId));
  return (
    <MailWorkspace
      filter={{ folderId }}
      title={folder?.name ?? "Folder"}
      description={folder ? "Custom folder" : "Folder not found"}
    />
  );
}
