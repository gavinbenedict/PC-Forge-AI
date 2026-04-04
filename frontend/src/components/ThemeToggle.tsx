"use client";
import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [theme, setTheme] = useState("dark");
  const [mounted, setMounted] = useState(false);

  // Hydration guard: don't render until client-side
  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem("pcforge_theme");
    if (saved) setTheme(saved);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("pcforge_theme", theme);
  }, [theme, mounted]);

  const toggleTheme = () =>
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));

  if (!mounted) return null;

  return (
    <button
      onClick={toggleTheme}
      aria-label="Toggle theme"
      style={{
        position: "fixed",
        bottom: "24px",
        right: "24px",
        zIndex: 9999,
        padding: "8px 12px",
        borderRadius: "10px",
        border: "1px solid var(--border-active)",
        background: "var(--bg-card)",
        color: "var(--text-primary)",
        cursor: "pointer",
        fontSize: 18,
        lineHeight: 1,
        boxShadow: "0 2px 12px rgba(0,0,0,0.25)",
        transition: "background 150ms ease, border-color 150ms ease",
      }}
      onMouseEnter={(e) =>
        ((e.currentTarget as HTMLButtonElement).style.background =
          "var(--bg-card-hover)")
      }
      onMouseLeave={(e) =>
        ((e.currentTarget as HTMLButtonElement).style.background =
          "var(--bg-card)")
      }
    >
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}
