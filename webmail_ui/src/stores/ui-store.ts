import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Density, ReadingPanePlacement, Theme, UserPreferences } from "@/types/mail";

export type ListView = "all" | "unread" | "focused" | "other" | "attachments" | "mentions";

interface UIState {
  selectedThreadId: string | null;
  selectedMessageId: string | null;
  selectedRowIds: string[];
  listView: ListView;
  sidebarCollapsed: boolean;
  // overlays
  shortcutsOpen: boolean;
  paletteOpen: boolean;
  newFolderOpen: boolean;
  moveToOpen: boolean;
  snoozeOpen: boolean;
  categorizeOpen: boolean;

  setSelectedThread: (id: string | null) => void;
  setSelectedMessage: (id: string | null) => void;
  setSelectedRowIds: (ids: string[]) => void;
  toggleRowSelected: (id: string) => void;
  clearSelection: () => void;

  setListView: (v: ListView) => void;
  setSidebarCollapsed: (v: boolean) => void;

  openShortcuts: (v?: boolean) => void;
  openPalette: (v?: boolean) => void;
  openNewFolder: (v?: boolean) => void;
  openMoveTo: (v?: boolean) => void;
  openSnooze: (v?: boolean) => void;
  openCategorize: (v?: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  selectedThreadId: null,
  selectedMessageId: null,
  selectedRowIds: [],
  listView: "all",
  sidebarCollapsed: false,
  shortcutsOpen: false,
  paletteOpen: false,
  newFolderOpen: false,
  moveToOpen: false,
  snoozeOpen: false,
  categorizeOpen: false,

  setSelectedThread: (id) =>
    set({ selectedThreadId: id, selectedMessageId: null, selectedRowIds: [] }),
  setSelectedMessage: (id) => set({ selectedMessageId: id }),
  setSelectedRowIds: (ids) => set({ selectedRowIds: ids }),
  toggleRowSelected: (id) =>
    set((s) => ({
      selectedRowIds: s.selectedRowIds.includes(id)
        ? s.selectedRowIds.filter((x) => x !== id)
        : [...s.selectedRowIds, id],
    })),
  clearSelection: () => set({ selectedRowIds: [] }),

  setListView: (listView) => set({ listView }),
  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),

  openShortcuts: (v) => set((s) => ({ shortcutsOpen: v ?? !s.shortcutsOpen })),
  openPalette: (v) => set((s) => ({ paletteOpen: v ?? !s.paletteOpen })),
  openNewFolder: (v) => set((s) => ({ newFolderOpen: v ?? !s.newFolderOpen })),
  openMoveTo: (v) => set((s) => ({ moveToOpen: v ?? !s.moveToOpen })),
  openSnooze: (v) => set((s) => ({ snoozeOpen: v ?? !s.snoozeOpen })),
  openCategorize: (v) => set((s) => ({ categorizeOpen: v ?? !s.categorizeOpen })),
}));

// ─── Preferences (persisted) ───────────────────────────────────────────────
const DEFAULT_PREFS: UserPreferences = {
  density: "comfortable",
  readingPane: "right",
  conversationView: true,
  focusedInbox: true,
  defaultSort: "date-desc",
  previewLines: 2,
  theme: "light",
  defaultReply: "reply",
  notifications: { desktop: true, sound: false, onlyFocused: true },
  outOfOffice: { enabled: false, message: "" },
  shortcutsEnabled: true,
};

interface PrefsState {
  prefs: UserPreferences;
  setDensity: (d: Density) => void;
  setReadingPane: (p: ReadingPanePlacement) => void;
  setTheme: (t: Theme) => void;
  patch: (p: Partial<UserPreferences>) => void;
}

export const usePrefsStore = create<PrefsState>()(
  persist(
    (set) => ({
      prefs: DEFAULT_PREFS,
      setDensity: (density) => set((s) => ({ prefs: { ...s.prefs, density } })),
      setReadingPane: (readingPane) => set((s) => ({ prefs: { ...s.prefs, readingPane } })),
      setTheme: (theme) => set((s) => ({ prefs: { ...s.prefs, theme } })),
      patch: (p) => set((s) => ({ prefs: { ...s.prefs, ...p } })),
    }),
    { name: "psense-mail-prefs", version: 1 },
  ),
);
