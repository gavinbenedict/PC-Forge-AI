"use client";
import Link from "next/link";
import ParticleCanvas from "./ParticleCanvas";

const FEATURES = [
  {
    tag: "INTELLIGENCE",
    title: "Smart Recommendations",
    desc: "Automatically infers missing components based on your usage profile, budget tier, and hardware signals. Every gap in your build is filled intelligently.",
  },
  {
    tag: "VALIDATION",
    title: "8-Rule Compatibility Engine",
    desc: "Checks CPU socket ↔ motherboard, RAM type, GPU clearance, PSU headroom, cooler height, and storage interface. Errors surface before you spend.",
  },
  {
    tag: "PRICING",
    title: "Hybrid Market Pricing",
    desc: "Simulated real-time prices from Newegg, Amazon, Best Buy and B&H Photo. ML fallback for rare or new components not yet in the price database.",
  },
  {
    tag: "ML MODEL",
    title: "XGBoost Price Prediction",
    desc: "Trained on hardware spec features. R² = 0.9755, MAE ≈ $26. Predicts market price from cores, VRAM, TDP, and category when live data is unavailable.",
  },
  {
    tag: "EXPORT",
    title: "CSV & Excel Reports",
    desc: "Download a 6-sheet styled Excel workbook or flat CSV with your full build, pricing breakdown, compatibility report, and architect notes.",
  },
  {
    tag: "ARCHITECTURE",
    title: "Dataset-Driven Catalogue",
    desc: "Every component is sourced from a preprocessed master catalogue with GPU VRAM variants, AIB sub-models, and RAM/storage capacity expansion built in.",
  },
] as const;

const HOW_STEPS = [
  {
    n: "01",
    title: "Describe Your Build",
    desc: "Provide as much or as little as you know — CPU only, GPU + budget, or full specs. Partial inputs are welcome.",
  },
  {
    n: "02",
    title: "AI Fills the Gaps",
    desc: "The recommendation engine selects compatible missing parts based on your tier, usage, and socket requirements.",
  },
  {
    n: "03",
    title: "Get Your Full Report",
    desc: "Receive a detailed analysis: component list, pricing breakdown, compatibility status, and export-ready data.",
  },
] as const;

export default function HomePage() {
  return (
    <>
      {/* Particle background */}
      <ParticleCanvas />

      {/* ── HERO ─────────────────────────────────────────────────────── */}
      <section className="hero">
        <div className="hero-eyebrow">V2.0 — DATASET DRIVEN</div>

        <h1 className="hero-title animate-fade-in">
          INTELLIGENT<br />
          PC BUILD<span className="slash"> //</span><br />
          ANALYSIS
          <span className="cursor" />
        </h1>

        <p className="hero-sub animate-fade-in" style={{ animationDelay: "80ms" }}>
          PCForge AI analyses your custom PC specification, validates component
          compatibility, recommends missing parts, and estimates real market prices —
          all in a single request.
        </p>

        <div className="hero-cta animate-fade-in" style={{ animationDelay: "160ms" }}>
          <Link href="/builder" className="btn btn-cta btn-lg">
            &gt; Start Build
          </Link>
          <a href="#features" className="btn btn-secondary btn-lg">
            Explore Features
          </a>
        </div>

        {/* Stats bar */}
        <div
          className="stats-bar animate-slide-up"
          style={{ marginTop: 64, animationDelay: "240ms" }}
        >
          {[
            { n: "500+", label: "Component SKUs" },
            { n: "8", label: "Compat Rules" },
            { n: "97.5%", label: "Model R²" },
            { n: "6", label: "Export Sheets" },
          ].map((s) => (
            <div className="stat-bar-item" key={s.label}>
              <span className="stat-bar-num">{s.n}</span>
              <span className="stat-bar-label">{s.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────────────────── */}
      <section id="features" className="section-block">
        <div className="container">
          <div
            style={{
              textAlign: "center",
              marginBottom: 40,
            }}
          >
            <p className="hero-eyebrow" style={{ justifyContent: "center" }}>
              CAPABILITIES
            </p>
            <h2
              style={{
                fontSize: "clamp(24px, 4vw, 36px)",
                fontWeight: 800,
                letterSpacing: "-0.03em",
              }}
            >
              EVERYTHING A PC BUILDER NEEDS
            </h2>
          </div>

          <div className="features-grid stagger">
            {FEATURES.map((f) => (
              <div className="feature-card animate-fade-in" key={f.title}>
                <span className="feature-tag">{f.tag}</span>
                <h3 className="feature-title">{f.title}</h3>
                <p className="feature-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────────────────────── */}
      <section id="how" className="section-block">
        <div className="container">
          <div style={{ textAlign: "center", marginBottom: 40 }}>
            <p className="hero-eyebrow" style={{ justifyContent: "center" }}>
              WORKFLOW
            </p>
            <h2
              style={{
                fontSize: "clamp(24px, 4vw, 36px)",
                fontWeight: 800,
                letterSpacing: "-0.03em",
              }}
            >
              THREE STEPS TO A COMPLETE BUILD
            </h2>
          </div>

          <div className="how-grid">
            {HOW_STEPS.map((s) => (
              <div className="how-step animate-slide-up" key={s.n}>
                <span className="how-num">{s.n}</span>
                <h3 className="how-step-title">{s.title}</h3>
                <p className="how-step-desc">{s.desc}</p>
              </div>
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: 48 }}>
            <Link href="/builder" className="btn btn-primary btn-lg">
              &gt; Launch Builder
            </Link>
          </div>
        </div>
      </section>



      <section id="contact" className="section-block">
        <div className="container">
          <div style={{ textAlign: "center", marginBottom: 40 }}>
            <p className="hero-eyebrow" style={{ justifyContent: "center" }}>
              CONTACTS
            </p>
            <h2
              style={{
                fontSize: "clamp(24px, 4vw, 36px)",
                fontWeight: 800,
                letterSpacing: "-0.03em",
              }}
            >
              CONTACT US AT
            </h2>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: "20px",
              marginTop: 10,
              flexWrap: "wrap",
            }}
          >
            <Link
              href="mailto:gav.benedict2005@gmail.com"
              className="btn btn-primary btn-lg"
              style={{ display: "flex", alignItems: "center", gap: "8px" }}
            >
              &gt; Email
              <svg
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                viewBox="0 0 24 24"
              >
                <rect x="3" y="5" width="18" height="14" rx="2" ry="2" />
                <polyline points="3,7 12,13 21,7" />
              </svg>
            </Link>

            <Link
              href="https://github.com/gavinbenedict"
              className="btn btn-primary btn-lg"
              style={{ display: "flex", alignItems: "center", gap: "8px" }}   // ← added
            >
              &gt; Github
              <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24">   {/* ← added */}
                <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.85 10.91.57.1.78-.25.78-.55v-2.1c-3.19.69-3.86-1.54-3.86-1.54-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.75 2.67 1.25 3.32.96.1-.74.4-1.25.72-1.54-2.55-.29-5.23-1.28-5.23-5.69 0-1.26.45-2.3 1.18-3.11-.12-.29-.51-1.45.11-3.03 0 0 .97-.31 3.18 1.18a11.06 11.06 0 0 1 5.8 0c2.21-1.49 3.18-1.18 3.18-1.18.62 1.58.23 2.74.11 3.03.73.81 1.18 1.85 1.18 3.11 0 4.42-2.69 5.4-5.26 5.69.41.35.78 1.04.78 2.1v3.11c0 .3.21.66.79.55A11.51 11.51 0 0 0 23.5 12c0-6.35-5.15-11.5-11.5-11.5z" />
              </svg>
            </Link>

            <Link
              href="https://wa.me/qr/WUABCMZBRXG4K1"
              className="btn btn-primary btn-lg"
              style={{ display: "flex", alignItems: "center", gap: "8px" }}   // ← added
            >
              &gt; Whatsapp
              <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24">   {/* ← added */}
                <path d="M20.52 3.48A11.82 11.82 0 0 0 12.02 0C5.39 0 .02 5.37.02 12c0 2.11.55 4.18 1.6 6.01L0 24l6.2-1.62A11.93 11.93 0 0 0 12.02 24c6.63 0 12-5.37 12-12 0-3.2-1.25-6.2-3.5-8.52zM12.02 22c-1.8 0-3.57-.48-5.13-1.38l-.37-.22-3.68.96.98-3.59-.24-.37A9.96 9.96 0 0 1 2.02 12c0-5.52 4.48-10 10-10 2.67 0 5.18 1.04 7.07 2.93A9.93 9.93 0 0 1 22.02 12c0 5.52-4.48 10-10 10zm5.46-7.38c-.3-.15-1.77-.87-2.05-.97-.27-.1-.47-.15-.67.15-.2.3-.77.97-.95 1.17-.17.2-.35.22-.65.07-.3-.15-1.26-.46-2.4-1.47-.89-.79-1.5-1.76-1.67-2.06-.17-.3-.02-.46.13-.6.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.07-.15-.67-1.62-.92-2.22-.24-.58-.48-.5-.67-.5-.17 0-.37-.02-.57-.02s-.52.07-.8.37c-.27.3-1.05 1.02-1.05 2.5s1.07 2.9 1.22 3.1c.15.2 2.1 3.2 5.08 4.49.71.31 1.27.5 1.7.64.71.22 1.36.19 1.87.12.57-.08 1.77-.72 2.02-1.42.25-.7.25-1.3.17-1.42-.07-.12-.27-.2-.57-.35z" />
              </svg>
            </Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────────── */}
      <footer
        style={{
          borderTop: "1px solid var(--border)",
          padding: "32px 24px",
          textAlign: "center",
        }}
      >
        <div className="container">
          <p className="term-label" style={{ justifyContent: "center", display: "flex" }}>
            PCFORGE AI v2.0 — Intelligent Build Analysis
            by Gavin N Benedict
          </p>
          <p
            style={{
              fontSize: 11,
              color: "var(--text-muted)",
              marginTop: 8,
            }}
          >
            Prices are simulated. Always verify current market pricing before purchasing.
          </p>
        </div>
      </footer>
    </>
  );
}
