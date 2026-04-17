import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ComposeDraft, MailRecipient } from "@/types/mail";

interface ComposeState {
  drafts: ComposeDraft[];
  open: ComposeDraft | null; // currently visible compose window
  openCompose: (init?: Partial<ComposeDraft>) => void;
  closeCompose: () => void;
  updateOpen: (patch: Partial<ComposeDraft>) => void;
  saveDraft: () => void;
  discardDraft: (id?: string) => void;
  toggleExpanded: () => void;
  toggleMinimized: () => void;
}

function emptyDraft(init?: Partial<ComposeDraft>): ComposeDraft {
  return {
    id: `d-${Date.now()}`,
    to: [] as MailRecipient[],
    cc: [],
    bcc: [],
    subject: "",
    bodyHtml: "",
    showCc: false,
    showBcc: false,
    expanded: false,
    attachments: [],
    ...init,
  };
}

export const useComposeStore = create<ComposeState>()(
  persist(
    (set, get) => ({
      drafts: [],
      open: null,
      openCompose: (init) => set({ open: emptyDraft(init) }),
      closeCompose: () => set({ open: null }),
      updateOpen: (patch) => set((s) => (s.open ? { open: { ...s.open, ...patch } } : s)),
      saveDraft: () => {
        const open = get().open;
        if (!open) return;
        const lastSavedAt = new Date().toISOString();
        const next = { ...open, lastSavedAt };
        set((s) => ({
          open: next,
          drafts: s.drafts.find((d) => d.id === next.id)
            ? s.drafts.map((d) => (d.id === next.id ? next : d))
            : [next, ...s.drafts],
        }));
      },
      discardDraft: (id) =>
        set((s) => {
          const targetId = id ?? s.open?.id;
          return {
            open: targetId === s.open?.id ? null : s.open,
            drafts: s.drafts.filter((d) => d.id !== targetId),
          };
        }),
      toggleExpanded: () =>
        set((s) => (s.open ? { open: { ...s.open, expanded: !s.open.expanded, minimized: false } } : s)),
      toggleMinimized: () =>
        set((s) => (s.open ? { open: { ...s.open, minimized: !s.open.minimized } } : s)),
    }),
    { name: "psense-compose", version: 1 },
  ),
);
