import type { MailFolder } from "@/types/mail";

export const SYSTEM_FOLDERS: MailFolder[] = [
  { id: "inbox", name: "Inbox", system: true },
  { id: "focused", name: "Focused", system: true },
  { id: "other", name: "Other", system: true },
  { id: "drafts", name: "Drafts", system: true },
  { id: "sent", name: "Sent", system: true },
  { id: "archive", name: "Archive", system: true },
  { id: "snoozed", name: "Snoozed", system: true },
  { id: "flagged", name: "Flagged", system: true },
  { id: "deleted", name: "Deleted", system: true },
  { id: "junk", name: "Junk", system: true },
];

export const CUSTOM_FOLDERS: MailFolder[] = [
  { id: "f-clients", name: "Clients" },
  { id: "f-finance", name: "Finance & Billing" },
  { id: "f-hiring", name: "Hiring 2026" },
  { id: "f-projects", name: "Projects" },
  { id: "f-receipts", name: "Receipts" },
];

export const FAVORITE_FOLDER_IDS = ["inbox", "flagged", "f-clients"];
