"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export default function Navbar() {
  const path = usePathname();

  // ── Theme state (owns the global data-theme attribute) ─────────
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

  return (
    <nav className="navbar">
      {/* Brand */}
      <Link href="/" className="navbar-brand">
        <span className="brand-icon">⚡</span>
        <span>
          PCFORGE<span className="brand-slash">//</span>AI
        </span>
      </Link>

      {/* Nav links */}
      <div className="navbar-nav">
        <Link
          href="/builder"
          className={`nav-link ${path === "/builder" ? "active" : ""}`}
        >
          ⚙ Build
        </Link>
        <Link href="/#features" className="nav-link">
          Features
        </Link>
        <Link href="/#how" className="nav-link">
          How It Works
        </Link>
      </div>

      {/* Actions — Start Build + theme toggle */}
      <div className="navbar-actions">
        {/* Terminal-style theme toggle */}
        {mounted && (
          <button
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            style={{
              display:        "inline-flex",
              alignItems:     "center",
              gap:            "6px",
              padding:        "6px 12px",
              borderRadius:   "4px",
              border:         "1px solid var(--border-subtle)",
              background:     "transparent",
              fontFamily:     "var(--font)",
              fontSize:       "10px",
              fontWeight:     700,
              letterSpacing:  "0.16em",
              color:          "var(--text-muted)",
              cursor:         "pointer",
              transition:     "color 0.2s ease, border-color 0.2s ease",
              whiteSpace:     "nowrap",
            }}
            onMouseEnter={(e) => {
              const b = e.currentTarget as HTMLButtonElement;
              b.style.color       = "var(--text-main)";
              b.style.borderColor = "var(--text-main)";
            }}
            onMouseLeave={(e) => {
              const b = e.currentTarget as HTMLButtonElement;
              b.style.color       = "var(--text-muted)";
              b.style.borderColor = "var(--border-subtle)";
            }}
          >
            {theme === "dark" ? "☀ LIGHT" : "🌙 DARK"}
          </button>
        )}

        <Link href="/builder" className="btn btn-primary btn-sm">
          &gt; Start Build
        </Link>
      </div>
    </nav>
  );
}
