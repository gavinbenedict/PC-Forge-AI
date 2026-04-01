"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const path = usePathname();

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
        <Link
          href="/#features"
          className="nav-link"
        >
          Features
        </Link>
        <Link
          href="/#how"
          className="nav-link"
        >
          How It Works
        </Link>
      </div>

      {/* Actions */}
      <div className="navbar-actions">
        <Link href="/builder" className="btn btn-primary btn-sm">
          &gt; Start Build
        </Link>
      </div>
    </nav>
  );
}
