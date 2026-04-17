import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";

export const Route = createFileRoute("/_app/mail/search")({
  validateSearch: (search: Record<string, unknown>) => ({
    q: typeof search.q === "string" ? search.q : "",
  }),
  component: SearchView,
});

function SearchView() {
  const { q } = Route.useSearch();
  return (
    <MailWorkspace
      filter={{ query: q }}
      title={q ? `Search: ${q}` : "Search"}
      description={q ? "Results across all folders" : "Type a query in the header to search"}
    />
  );
}
