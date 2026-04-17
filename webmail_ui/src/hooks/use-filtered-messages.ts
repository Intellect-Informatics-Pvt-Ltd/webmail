import { useMemo } from "react";
import { useMailStore } from "@/stores/mail-store";
import { useUIStore } from "@/stores/ui-store";
import type { MailMessage } from "@/types/mail";

export type FolderKey =
  | "inbox"
  | "focused"
  | "other"
  | "drafts"
  | "sent"
  | "archive"
  | "snoozed"
  | "flagged"
  | "deleted"
  | "junk"
  | "all";

export interface MessageFilter {
  folderId?: string; // custom folder id or system folder
  folderKey?: FolderKey;
  categoryId?: string;
  query?: string;
}

function matchesQuery(m: MailMessage, q: string): boolean {
  if (!q) return true;
  const tokens = q.split(/\s+/).filter(Boolean);
  const haystack = `${m.subject} ${m.preview} ${m.sender.name} ${m.sender.email} ${m.recipients.map((r) => r.email).join(" ")}`.toLowerCase();
  return tokens.every((tok) => {
    const t = tok.toLowerCase();
    if (t.startsWith("from:")) return m.sender.email.toLowerCase().includes(t.slice(5));
    if (t.startsWith("to:"))
      return m.recipients.some((r) => r.email.toLowerCase().includes(t.slice(3)));
    if (t === "has:attachment") return m.hasAttachments;
    if (t === "is:unread") return !m.isRead;
    if (t === "is:flagged") return m.isFlagged;
    if (t.startsWith("subject:")) return m.subject.toLowerCase().includes(t.slice(8));
    return haystack.includes(t);
  });
}

export function useFilteredMessages(filter: MessageFilter): MailMessage[] {
  const messages = useMailStore((s) => s.messages);
  const view = useUIStore((s) => s.listView);

  return useMemo(() => {
    let out = messages.slice();

    // folder scoping
    if (filter.folderKey === "flagged") {
      out = out.filter((m) => m.isFlagged && m.folderId !== "deleted");
    } else if (filter.folderKey === "focused") {
      out = out.filter((m) => m.folderId === "inbox" && m.isFocused);
    } else if (filter.folderKey === "other") {
      out = out.filter((m) => m.folderId === "inbox" && !m.isFocused);
    } else if (filter.folderKey && filter.folderKey !== "all") {
      out = out.filter((m) => m.folderId === filter.folderKey);
    } else if (filter.folderId) {
      out = out.filter((m) => m.folderId === filter.folderId);
    }

    // category scoping
    if (filter.categoryId) {
      out = out.filter((m) => m.categories.includes(filter.categoryId!));
    }

    // query
    if (filter.query) {
      out = out.filter((m) => matchesQuery(m, filter.query!));
    }

    // tab view
    switch (view) {
      case "unread":
        out = out.filter((m) => !m.isRead);
        break;
      case "focused":
        out = out.filter((m) => m.isFocused);
        break;
      case "other":
        out = out.filter((m) => !m.isFocused);
        break;
      case "attachments":
        out = out.filter((m) => m.hasAttachments);
        break;
      case "mentions":
        out = out.filter((m) => m.hasMentions);
        break;
    }

    // sort: pinned first, then date desc
    out.sort((a, b) => {
      if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1;
      return new Date(b.receivedAt).getTime() - new Date(a.receivedAt).getTime();
    });
    return out;
  }, [messages, filter.folderKey, filter.folderId, filter.categoryId, filter.query, view]);
}
