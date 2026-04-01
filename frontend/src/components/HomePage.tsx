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
          BUILD<span className="slash"> //</span><br />
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
            { n: "8",    label: "Compat Rules" },
            { n: "97.5%",label: "Model R²" },
            { n: "6",    label: "Export Sheets" },
          ].map((s) => (
            <div className="stat-bar-item" key={s.label}>
              <span className="stat-bar-num">{s.n}</span>
              <span className="stat-bar-label">{s.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────────────────── */}
      <section id="features" style={{ padding: "80px 0" }}>
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
              Everything an engineer needs
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
      <section id="how" style={{ padding: "80px 0" }}>
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
              Three steps to a complete build
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
