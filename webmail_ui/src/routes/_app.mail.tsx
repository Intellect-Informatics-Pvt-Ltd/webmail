import { Outlet, createFileRoute } from "@tanstack/react-router";
import { MailSidebar } from "@/components/layout/mail-sidebar";

export const Route = createFileRoute("/_app/mail")({
  component: MailLayout,
});

function MailLayout() {
  return (
    <div className="flex h-full flex-1 overflow-hidden">
      <MailSidebar />
      <div className="flex flex-1 overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
