import { create } from "zustand";

interface UiStore {
  sidebarOpen: boolean;
  activeSection: "dashboard" | "chat" | "devices" | "settings";
  notifications: Notification[];
  setSidebarOpen: (open: boolean) => void;
  setActiveSection: (section: UiStore["activeSection"]) => void;
  addNotification: (n: Omit<Notification, "id" | "ts">) => void;
  removeNotification: (id: string) => void;
}

interface Notification {
  id: string;
  type: "info" | "warning" | "error" | "success";
  message: string;
  ts: number;
}

export const useUiStore = create<UiStore>((set) => ({
  sidebarOpen: true,
  activeSection: "dashboard",
  notifications: [],

  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setActiveSection: (section) => set({ activeSection: section }),

  addNotification: (n) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        { ...n, id: crypto.randomUUID(), ts: Date.now() },
      ].slice(-20),
    })),

  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
}));
