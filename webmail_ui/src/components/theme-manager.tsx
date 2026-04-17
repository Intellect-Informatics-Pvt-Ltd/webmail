import { useEffect } from "react";
import { usePrefsStore } from "@/stores/ui-store";

/**
 * Applies theme + density to <html> based on persisted preferences.
 * Mount once in the app root.
 */
export function ThemeManager() {
  const theme = usePrefsStore((s) => s.prefs.theme);
  const density = usePrefsStore((s) => s.prefs.density);

  useEffect(() => {
    const root = document.documentElement;
    const apply = () => {
      const isDark =
        theme === "dark" ||
        (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
      root.classList.toggle("dark", isDark);
    };
    apply();
    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      mq.addEventListener("change", apply);
      return () => mq.removeEventListener("change", apply);
    }
  }, [theme]);

  useEffect(() => {
    document.documentElement.dataset.density = density;
  }, [density]);

  return null;
}
