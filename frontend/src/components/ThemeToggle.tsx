"use client";
import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [theme, setTheme] = useState("dark");
  const [mounted, setMounted] = useState(false);

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
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      style={{
        /* Positioning */
        position:   "fixed",
        bottom:     "24px",
        right:      "24px",
        zIndex:     9999,

        /* Sizing */
        padding:    "7px 14px",
        borderRadius: "6px",

        /* Terminal aesthetic */
        fontFamily:     "var(--font)",
        fontSize:       "10px",
        fontWeight:     700,
        letterSpacing:  "0.18em",
        lineHeight:     1,

        /* Colors — always dark/glassy regardless of page theme */
        background:     "rgba(0, 0, 0, 0.82)",
        backdropFilter: "blur(10px)",
        WebkitBackdropFilter: "blur(10px)",
        color:          "#b0b0b0",
        border:         "1px solid #3a3a3a",

        cursor:  "pointer",
        boxShadow: "0 2px 16px rgba(0,0,0,0.5)",

        /* Transition only for hover — not caught by global rule */
        transition: "color 0.15s ease, border-color 0.15s ease",
      }}
      onMouseEnter={(e) => {
        const btn = e.currentTarget as HTMLButtonElement;
        btn.style.color       = "#ffffff";
        btn.style.borderColor = "#ffffff";
      }}
      onMouseLeave={(e) => {
        const btn = e.currentTarget as HTMLButtonElement;
        btn.style.color       = "#b0b0b0";
        btn.style.borderColor = "#3a3a3a";
      }}
    >
      {theme === "dark" ? "LIGHT" : "DARK"}
    </button>
  );
}
