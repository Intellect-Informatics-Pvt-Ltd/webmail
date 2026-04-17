import { Group as GroupRaw, Panel, Separator as SeparatorRaw } from "react-resizable-panels";

// react-resizable-panels has loose ambient typings in this template; cast to any-prop component.
const Group = GroupRaw as unknown as React.FC<
  React.PropsWithChildren<{
    direction: "horizontal" | "vertical";
    className?: string;
    autoSaveId?: string;
  }>
>;
const Separator = SeparatorRaw as unknown as React.FC<React.PropsWithChildren<{ className?: string }>>;
import { GripVertical } from "lucide-react";
import { cn } from "@/lib/utils";
import { MessageList } from "@/components/mail/message-list";
import { ReadingPane } from "@/components/mail/reading-pane";
import { usePrefsStore } from "@/stores/ui-store";
import type { MessageFilter } from "@/hooks/use-filtered-messages";

interface MailWorkspaceProps {
  filter: MessageFilter;
  title: string;
  description?: string;
}

export function MailWorkspace({ filter, title, description }: MailWorkspaceProps) {
  const placement = usePrefsStore((s) => s.prefs.readingPane);

  if (placement === "off") {
    return (
      <div className="h-full w-full">
        <MessageList filter={filter} title={title} description={description} />
      </div>
    );
  }

  const direction = placement === "bottom" ? "vertical" : "horizontal";
  const key = `mail-workspace-${direction}`;

  return (
    <Group
      key={key}
      direction={direction}
      className={cn("flex h-full w-full", direction === "vertical" && "flex-col")}
      autoSaveId={key}
    >
      <Panel defaultSize={direction === "vertical" ? 45 : 38} minSize={25}>
        <MessageList filter={filter} title={title} description={description} />
      </Panel>
      <Separator
        className={cn(
          "relative flex items-center justify-center bg-border transition-colors hover:bg-primary/40",
          direction === "horizontal" ? "w-px" : "h-px",
        )}
      >
        <div
          className={cn(
            "z-10 flex items-center justify-center rounded-sm border border-border bg-background opacity-0 hover:opacity-100",
            direction === "horizontal" ? "h-6 w-3" : "h-3 w-6 rotate-90",
          )}
        >
          <GripVertical className="h-2.5 w-2.5 text-muted-foreground" />
        </div>
      </Separator>
      <Panel defaultSize={direction === "vertical" ? 55 : 62} minSize={30}>
        <ReadingPane />
      </Panel>
    </Group>
  );
}
