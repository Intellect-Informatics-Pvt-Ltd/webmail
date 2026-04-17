import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  MailMessage,
  MailFolder,
  MailRule,
  MailTemplate,
  MailSignature,
} from "@/types/mail";
import { MESSAGES, RULES, TEMPLATES, SIGNATURES } from "@/data/messages";
import { SYSTEM_FOLDERS, CUSTOM_FOLDERS, FAVORITE_FOLDER_IDS } from "@/data/folders";

interface MailState {
  messages: MailMessage[];
  folders: MailFolder[];
  customFolders: MailFolder[];
  favorites: string[];
  rules: MailRule[];
  templates: MailTemplate[];
  signatures: MailSignature[];

  // mutations
  toggleRead: (ids: string[], read?: boolean) => void;
  toggleFlag: (ids: string[]) => void;
  togglePin: (ids: string[]) => void;
  moveTo: (ids: string[], folderId: string) => void;
  archive: (ids: string[]) => void;
  remove: (ids: string[]) => void;
  snooze: (ids: string[], untilIso: string) => void;
  categorize: (ids: string[], categoryId: string) => void;

  upsertMessage: (m: MailMessage) => void;

  addFolder: (name: string) => MailFolder;
  renameFolder: (id: string, name: string) => void;
  deleteFolder: (id: string) => void;
  toggleFavorite: (folderId: string) => void;

  addRule: (rule: MailRule) => void;
  updateRule: (rule: MailRule) => void;
  deleteRule: (id: string) => void;

  addTemplate: (tpl: MailTemplate) => void;
  updateTemplate: (tpl: MailTemplate) => void;
  deleteTemplate: (id: string) => void;
}

export const useMailStore = create<MailState>()(
  persist(
    (set) => ({
      messages: MESSAGES,
      folders: SYSTEM_FOLDERS,
      customFolders: CUSTOM_FOLDERS,
      favorites: FAVORITE_FOLDER_IDS,
      rules: RULES,
      templates: TEMPLATES,
      signatures: SIGNATURES,

      toggleRead: (ids, read) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            ids.includes(m.id) ? { ...m, isRead: read ?? !m.isRead } : m,
          ),
        })),
      toggleFlag: (ids) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            ids.includes(m.id) ? { ...m, isFlagged: !m.isFlagged } : m,
          ),
        })),
      togglePin: (ids) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            ids.includes(m.id) ? { ...m, isPinned: !m.isPinned } : m,
          ),
        })),
      moveTo: (ids, folderId) =>
        set((s) => ({
          messages: s.messages.map((m) => (ids.includes(m.id) ? { ...m, folderId } : m)),
        })),
      archive: (ids) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            ids.includes(m.id) ? { ...m, folderId: "archive" } : m,
          ),
        })),
      remove: (ids) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            ids.includes(m.id) ? { ...m, folderId: "deleted" } : m,
          ),
        })),
      snooze: (ids, untilIso) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            ids.includes(m.id) ? { ...m, folderId: "snoozed", snoozedUntil: untilIso } : m,
          ),
        })),
      categorize: (ids, categoryId) =>
        set((s) => ({
          messages: s.messages.map((m) =>
            ids.includes(m.id)
              ? {
                  ...m,
                  categories: m.categories.includes(categoryId)
                    ? m.categories
                    : [...m.categories, categoryId],
                }
              : m,
          ),
        })),

      upsertMessage: (m) =>
        set((s) => {
          const exists = s.messages.find((x) => x.id === m.id);
          return {
            messages: exists
              ? s.messages.map((x) => (x.id === m.id ? m : x))
              : [m, ...s.messages],
          };
        }),

      addFolder: (name) => {
        const id = `f-${Date.now()}`;
        const folder: MailFolder = { id, name };
        set((s) => ({ customFolders: [...s.customFolders, folder] }));
        return folder;
      },
      renameFolder: (id, name) =>
        set((s) => ({
          customFolders: s.customFolders.map((f) => (f.id === id ? { ...f, name } : f)),
        })),
      deleteFolder: (id) =>
        set((s) => ({
          customFolders: s.customFolders.filter((f) => f.id !== id),
          favorites: s.favorites.filter((x) => x !== id),
        })),
      toggleFavorite: (folderId) =>
        set((s) => ({
          favorites: s.favorites.includes(folderId)
            ? s.favorites.filter((x) => x !== folderId)
            : [...s.favorites, folderId],
        })),

      addRule: (rule) => set((s) => ({ rules: [rule, ...s.rules] })),
      updateRule: (rule) =>
        set((s) => ({ rules: s.rules.map((r) => (r.id === rule.id ? rule : r)) })),
      deleteRule: (id) => set((s) => ({ rules: s.rules.filter((r) => r.id !== id) })),

      addTemplate: (tpl) => set((s) => ({ templates: [tpl, ...s.templates] })),
      updateTemplate: (tpl) =>
        set((s) => ({ templates: s.templates.map((t) => (t.id === tpl.id ? tpl : t)) })),
      deleteTemplate: (id) =>
        set((s) => ({ templates: s.templates.filter((t) => t.id !== id) })),
    }),
    {
      name: "psense-mail-data",
      version: 1,
    },
  ),
);
