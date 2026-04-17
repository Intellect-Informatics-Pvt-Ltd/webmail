import { createFileRoute } from "@tanstack/react-router";
import { MailWorkspace } from "@/components/mail/mail-workspace";
import { getCategory } from "@/data/categories";

export const Route = createFileRoute("/_app/mail/category/$categoryId")({
  component: CategoryView,
});

function CategoryView() {
  const { categoryId } = Route.useParams();
  const cat = getCategory(categoryId);
  return (
    <MailWorkspace
      filter={{ categoryId }}
      title={cat?.name ?? "Category"}
      description="Messages tagged with this category"
    />
  );
}
