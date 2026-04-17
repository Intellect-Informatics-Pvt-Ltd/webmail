import { create } from "zustand";
import { persist } from "zustand/middleware";
import { CONTACTS, type Contact, type ContactGroup } from "@/data/contacts";

interface ContactsState {
  contacts: Contact[];
  selectedGroup: ContactGroup | "all" | "pinned";
  query: string;
  setSelectedGroup: (g: ContactGroup | "all" | "pinned") => void;
  setQuery: (q: string) => void;
  togglePinned: (id: string) => void;
  addContact: (c: Contact) => void;
  updateContact: (c: Contact) => void;
  deleteContact: (id: string) => void;
}

export const useContactsStore = create<ContactsState>()(
  persist(
    (set) => ({
      contacts: CONTACTS,
      selectedGroup: "all",
      query: "",
      setSelectedGroup: (selectedGroup) => set({ selectedGroup }),
      setQuery: (query) => set({ query }),
      togglePinned: (id) =>
        set((s) => ({
          contacts: s.contacts.map((c) =>
            c.id === id ? { ...c, pinned: !c.pinned } : c,
          ),
        })),
      addContact: (c) => set((s) => ({ contacts: [c, ...s.contacts] })),
      updateContact: (c) =>
        set((s) => ({
          contacts: s.contacts.map((x) => (x.id === c.id ? c : x)),
        })),
      deleteContact: (id) =>
        set((s) => ({ contacts: s.contacts.filter((c) => c.id !== id) })),
    }),
    { name: "psense-contacts", version: 1 },
  ),
);
