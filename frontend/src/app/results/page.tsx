"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  type AnalyzeResponse,
  type PricedPart,
  exportExcel,
  exportCSV,
  downloadBlob,
} from "@/lib/api";

// ─── Tier config ──────────────────────────────────────────────────────────────

const TIER_CONFIG = {
  budget:       { label: "Budget",       color: "var(--text-secondary)" },
  "mid-range":  { label: "Mid-Range",    color: "var(--amber)" },
  "high-end":   { label: "High-End",     color: "var(--green)" },
  enthusiast:   { label: "Enthusiast",   color: "var(--red)" },
} as const;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(n: number, currency?: string) {
  // Large-valued currencies (INR, JPY etc.) don't show cents
  const noCents = currency && ["INR", "JPY"].includes(currency.toUpperCase());
  return n.toLocaleString("en-US", {
    minimumFractionDigits: noCents ? 0 : 2,
    maximumFractionDigits: noCents ? 0 : 2,
  });
}

function getSourceBadge(source: string) {
  if (source === "live")      return <span className="badge badge-green">Live</span>;
  if (source === "simulated") return <span className="badge badge-green">Simulated</span>;
  return <span className="badge badge-amber">Predicted</span>;
}

function getSeverityClass(severity: string) {
  if (severity === "error")   return "alert alert-error";
  if (severity === "warning") return "alert alert-warn";
  return "alert alert-info";
}

function getSeverityIcon(severity: string) {
  if (severity === "error")   return "✕";
  if (severity === "warning") return "⚠";
  return "ℹ";
}

// ─── Display name helper ─────────────────────────────────────────────────────
// Backend sometimes returns brand+model where model already contains the brand
// e.g. brand="AMD" model="AMD Ryzen 5 7600X" → show only model
function displayName(brand: string, model: string): string {
  if (!brand) return model;
  const b = brand.trim().toLowerCase();
  const m = model.trim().toLowerCase();
  if (m.startsWith(b)) return model.trim(); // model already contains brand
  return `${brand.trim()} ${model.trim()}`;
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────

const TABS = [
  { id: "overview",       label: "Overview" },
  { id: "build",          label: "Components" },
  { id: "pricing",        label: "Pricing" },
  { id: "compatibility",  label: "Compatibility" },
  { id: "recommendations",label: "Recommendations" },
  { id: "notes",          label: "Notes" },
] as const;

type TabId = (typeof TABS)[number]["id"];

// ─── Component Card ───────────────────────────────────────────────────────────

function CompCard({
  part,
  sym,
  currency,
  isAutoFilled,
}: {
  part: PricedPart;
  sym: string;
  currency: string;
  isAutoFilled?: boolean;
}) {
  return (
    <div className={`comp-card ${isAutoFilled ? "autofill" : ""}`}>
      <div className="comp-cat">
        <span>{part.category}</span>
        {isAutoFilled && (
          <span className="badge badge-amber">Auto-filled</span>
        )}
      </div>
      <div className="comp-model">
        {displayName(part.brand, part.model)}
      </div>
      <div
        className={`comp-price ${
          part.source === "predicted" ? "predicted" : ""
        }`}
      >
        {sym}{fmt(part.price_usd, currency)}
        <span
          style={{
            fontSize: 10,
            marginLeft: 6,
            color: "var(--text-muted)",
            fontWeight: 400,
          }}
        >
          {part.store}
        </span>
      </div>
    </div>
  );
}

// ─── Main results page ────────────────────────────────────────────────────────

export default function ResultsPage() {
  const router = useRouter();
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [exporting, setExporting] = useState<"excel" | "csv" | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load from sessionStorage
  useEffect(() => {
    const raw = sessionStorage.getItem("pcforge_result");
    if (!raw) {
      router.push("/builder");
      return;
    }
    try {
      setData(JSON.parse(raw));
    } catch {
      router.push("/builder");
    }
  }, [router]);


  if (!data) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <div className="spinner" style={{ width: 32, height: 32 }} />
        <p style={{ color: "var(--text-muted)", fontSize: 12 }}>
          Loading analysis<span className="loading-dots" />
        </p>
      </div>
    );
  }

  const tier      = data.inferred_tier;
  const tierCfg   = TIER_CONFIG[tier] || TIER_CONFIG["mid-range"];
  const summary   = data.price_summary;
  const sym       = summary.symbol || "$";
  const currency  = summary.currency || "USD";
  const compat    = data.compatibility;
  const recs      = data.recommendations;
  const errorCount = compat.issues.filter((i) => i.severity === "error").length;
  const warnCount  = compat.issues.filter((i) => i.severity === "warning").length;

  // ── Export handlers ────────────────────────────────────────────
  const handleExcel = async () => {
    setExporting("excel");
    try {
      const blob = await exportExcel(data);
      downloadBlob(blob, `pcforge-build-${data.build_id}.xlsx`);
    } catch {
      setError("Excel export failed. Is the backend running?");
    } finally {
      setExporting(null);
    }
  };

  const handleCSV = async () => {
    setExporting("csv");
    try {
      const blob = await exportCSV(data);
      downloadBlob(blob, `pcforge-build-${data.build_id}.csv`);
    } catch {
      setError("CSV export failed.");
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="results-layout content-layer">
      {/* ── Back to Builder (fixed bottom-left) ──────────────────── */}
      <button
        onClick={() => router.push("/builder")}
        aria-label="Back to builder"
        style={{
          position: "fixed",
          bottom: "24px",
          left: "24px",
          zIndex: 9999,
          padding: "8px 14px",
          borderRadius: "10px",
          border: "1px solid var(--border-active)",
          background: "var(--bg-card)",
          color: "var(--text-secondary)",
          cursor: "pointer",
          fontSize: 12,
          fontFamily: "var(--font)",
          fontWeight: 600,
          letterSpacing: "0.06em",
          boxShadow: "0 2px 12px rgba(0,0,0,0.25)",
          transition: "background 150ms ease, color 150ms ease",
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = "var(--bg-card-hover)";
          (e.currentTarget as HTMLButtonElement).style.color = "var(--text-primary)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = "var(--bg-card)";
          (e.currentTarget as HTMLButtonElement).style.color = "var(--text-secondary)";
        }}
      >
        ← Builder
      </button>
      {/* ── Results header ─────────────────────────────────────── */}
      <div className="results-header">
        <div className="container">
          <p className="results-build-id">// BUILD_ID: {data.build_id}</p>
          <h1 className="results-title">
            Build Analysis
            <span className="cursor" />
          </h1>

          <div className="results-tags">
            <span
              className="badge"
              style={{
                color: tierCfg.color,
                borderColor: tierCfg.color,
                background: "transparent",
              }}
            >
              {tierCfg.label}
            </span>
            {data.usage_type && (
              <span className="badge badge-gray">
                {data.usage_type.toUpperCase()}
              </span>
            )}
            <span
              className={`badge ${
                compat.status === "valid"
                  ? "badge-green"
                  : compat.status === "warning"
                  ? "badge-amber"
                  : "badge-red"
              }`}
            >
              {compat.status === "valid"
                ? "✓ Compatible"
                : compat.status === "warning"
                ? "⚠ Warnings"
                : "✕ Incompatible"}
            </span>
            {data.auto_filled_components.length > 0 && (
              <span className="badge badge-amber">
                {data.auto_filled_components.length} Auto-filled
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Tabs ──────────────────────────────────────────────── */}
      <div
        style={{
          borderBottom: "1px solid var(--border)",
          background: "var(--bg-surface)",
          position: "sticky",
          top: "var(--navbar-h)",
          zIndex: 10,
        }}
      >
        <div className="container">
          <div className="tabs">
            {TABS.map((t) => (
              <button
                key={t.id}
                className={`tab ${activeTab === t.id ? "active" : ""}`}
                onClick={() => setActiveTab(t.id)}
              >
                {t.id === "compatibility" && errorCount > 0 && (
                  <span
                    style={{
                      background: "var(--red)",
                      color: "#000",
                      fontSize: 9,
                      fontWeight: 800,
                      padding: "1px 5px",
                      borderRadius: 2,
                    }}
                  >
                    {errorCount}
                  </span>
                )}
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Tab content ───────────────────────────────────────── */}
      <div className="results-body animate-fade-in">
        {error && (
          <div className="alert alert-error" style={{ marginBottom: 24 }}>
            <span>⚠</span>
            <span>{error}</span>
          </div>
        )}

        {/* ── OVERVIEW ───────────────────────────────────────── */}
        {activeTab === "overview" && (
          <>
            {/* Price summary */}
            <div className="stat-grid" style={{ marginBottom: 24 }}>
              <div className="stat-block">
                <div className="stat-label">Total Cost</div>
                <div className="stat-value green">
                  {sym}{fmt(summary.total_combined_usd, currency)}
                </div>
              </div>
              <div className="stat-block">
                <div className="stat-label">Live Prices</div>
                <div className="stat-value">
                  {sym}{fmt(summary.total_live_usd, currency)}
                </div>
              </div>
              <div className="stat-block">
                <div className="stat-label">ML Predicted</div>
                <div className="stat-value amber">
                  {sym}{fmt(summary.total_predicted_usd, currency)}
                </div>
              </div>
              <div className="stat-block">
                <div className="stat-label">Market Low</div>
                <div className="stat-value">
                  {sym}{fmt(summary.market_range.min_price, currency)}
                </div>
              </div>
              <div className="stat-block">
                <div className="stat-label">Market High</div>
                <div className="stat-value">
                  {sym}{fmt(summary.market_range.max_price, currency)}
                </div>
              </div>
              <div className="stat-block">
                <div className="stat-label">Components</div>
                <div className="stat-value">
                  {data.pricing.length}
                </div>
              </div>
            </div>

            {/* Tier reasoning */}
            {recs.tier_reasoning && (
              <div className="panel" style={{ marginBottom: 24 }}>
                <div className="panel-header">
                  <span className="panel-title">Tier Analysis</span>
                  <span
                    style={{ color: tierCfg.color, fontSize: 11, fontWeight: 700 }}
                  >
                    {tierCfg.label}
                  </span>
                </div>
                <div className="panel-body">
                  <p
                    className="red-line-left"
                    style={{
                      fontSize: 13,
                      color: "var(--text-secondary)",
                      lineHeight: 1.7,
                    }}
                  >
                    {recs.tier_reasoning}
                  </p>
                </div>
              </div>
            )}

            {/* Component cards grid — sourced from data.pricing (always complete) */}
            <div className="section-title" style={{ marginBottom: 16 }}>
              Completed Build
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                gap: 10,
              }}
              className="stagger"
            >
              {data.pricing.map((part) => (
                <CompCard
                  key={`${part.category}-${part.model}`}
                  part={part}
                  sym={sym}
                  currency={currency}
                  isAutoFilled={data.auto_filled_components.includes(part.category)}
                />
              ))}
            </div>
          </>
        )}

        {/* ── COMPONENTS (BUILD) ─────────────────────────────── */}
        {activeTab === "build" && (
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">Component List</span>
              <span className="badge badge-gray">
                {data.completed_build.length} parts
              </span>
            </div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Brand</th>
                    <th>Model</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {data.completed_build.map((c) => (
                    <tr key={`${c.category}-${c.model}`}>
                      <td>
                        <span style={{ color: "var(--red)", marginRight: 6 }}>
                          &gt;
                        </span>
                        {c.category}
                      </td>
                      <td style={{ color: "var(--text-muted)" }}>
                        {c.brand}
                      </td>
                      <td className="td-model">{c.model}</td>
                      <td>
                        {c.is_auto_filled ? (
                          <span className="badge badge-amber">Auto-filled</span>
                        ) : (
                          <span className="badge badge-gray">User input</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── PRICING ────────────────────────────────────────── */}
        {activeTab === "pricing" && (
          <>
            <div className="stat-grid" style={{ marginBottom: 24 }}>
              <div className="stat-block">
                <div className="stat-label">Total (Combined)</div>
                <div className="stat-value green mono-val">
                  {sym}{fmt(summary.total_combined_usd, currency)}
                </div>
              </div>
              <div className="stat-block">
                <div className="stat-label">Simulated Prices</div>
                <div className="stat-value">{summary.live_parts_count}</div>
              </div>
              <div className="stat-block">
                <div className="stat-label">ML Predicted</div>
                <div className="stat-value amber">
                  {summary.predicted_parts_count}
                </div>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <span className="panel-title">Price Breakdown</span>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Model</th>
                      <th>Store</th>
                      <th>Source</th>
                      <th style={{ textAlign: "right" }}>Price ({currency})</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.pricing.map((p, i) => (
                      <tr key={i}>
                        <td style={{ color: "var(--text-muted)" }}>
                          {p.category}
                        </td>
                        <td className="td-model">{p.model}</td>
                        <td style={{ color: "var(--text-muted)" }}>
                          {p.store}
                        </td>
                        <td>{getSourceBadge(p.source)}</td>
                        <td
                          className={
                            p.source === "predicted" ? "td-pred" : "td-price"
                          }
                          style={{ textAlign: "right" }}
                        >
                          {sym}{fmt(p.price_usd, currency)}
                          {p.predicted_range && (
                            <span
                              style={{
                                fontSize: 10,
                                color: "var(--text-muted)",
                                display: "block",
                                fontWeight: 400,
                              }}
                            >
                              {sym}{fmt(p.predicted_range.min_price, currency)} –{" "}
                              {sym}{fmt(p.predicted_range.max_price, currency)}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {/* Total row */}
                    <tr>
                      <td
                        colSpan={4}
                        style={{
                          fontWeight: 700,
                          fontSize: 11,
                          letterSpacing: "0.1em",
                          textTransform: "uppercase",
                          color: "var(--text-muted)",
                        }}
                      >
                        Total
                      </td>
                      <td
                        style={{
                          textAlign: "right",
                          fontWeight: 800,
                          fontSize: 18,
                          color: "var(--green)",
                          fontVariantNumeric: "tabular-nums",
                        }}
                      >
                        {sym}{fmt(summary.total_combined_usd, currency)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {/* ── COMPATIBILITY ──────────────────────────────────── */}
        {activeTab === "compatibility" && (
          <>
            {/* Summary row */}
            <div className="stat-grid" style={{ marginBottom: 24 }}>
              <div className="stat-block">
                <div className="stat-label">Status</div>
                <div
                  className="stat-value"
                  style={{
                    color:
                      compat.status === "valid"
                        ? "var(--green)"
                        : compat.status === "warning"
                        ? "var(--amber)"
                        : "var(--red)",
                    fontSize: 16,
                  }}
                >
                  {compat.status.toUpperCase()}
                </div>
              </div>
              <div className="stat-block">
                <div className="stat-label">Checks Passed</div>
                <div className="stat-value green">{compat.passed_checks.length}</div>
              </div>
              <div className="stat-block">
                <div className="stat-label">Errors</div>
                <div className="stat-value red">{errorCount}</div>
              </div>
              <div className="stat-block">
                <div className="stat-label">Warnings</div>
                <div className="stat-value amber">{warnCount}</div>
              </div>
            </div>

            {/* Passed checks */}
            {compat.passed_checks.length > 0 && (
              <div className="panel" style={{ marginBottom: 16 }}>
                <div className="panel-header">
                  <span className="panel-title">Passed Checks</span>
                  <span className="badge badge-green">
                    {compat.passed_checks.length}
                  </span>
                </div>
                <div className="panel-body">
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                    }}
                  >
                    {compat.passed_checks.map((msg, i) => (
                      <div
                        key={i}
                        style={{
                          display: "flex",
                          gap: 10,
                          alignItems: "flex-start",
                          fontSize: 12,
                          color: "var(--text-secondary)",
                        }}
                      >
                        <span style={{ color: "var(--green)", flexShrink: 0 }}>
                          ✓
                        </span>
                        <span>{msg}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Issues */}
            {compat.issues.length > 0 && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                }}
                className="stagger"
              >
                {compat.issues.map((issue, i) => (
                  <div key={i} className={getSeverityClass(issue.severity)}>
                    <span style={{ flexShrink: 0, fontWeight: 800 }}>
                      {getSeverityIcon(issue.severity)}
                    </span>
                    <div>
                      <div
                        style={{
                          fontWeight: 700,
                          marginBottom: 4,
                          fontSize: 12,
                        }}
                      >
                        [{issue.component}] {issue.issue}
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          opacity: 0.8,
                        }}
                      >
                        Fix: {issue.suggested_fix}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {compat.issues.length === 0 && (
              <div className="alert alert-ok">
                <span>✓</span>
                <span>All compatibility checks passed. This build is fully compatible.</span>
              </div>
            )}
          </>
        )}

        {/* ── RECOMMENDATIONS ────────────────────────────────── */}
        {activeTab === "recommendations" && (
          <>
            <div className="panel" style={{ marginBottom: 16 }}>
              <div className="panel-header">
                <span className="panel-title">Recommended Parts</span>
                <span className="badge badge-gray">
                  {recs.recommended_parts.length} components
                </span>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Model</th>
                      <th>Reasoning</th>
                      <th style={{ textAlign: "right" }}>Price</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recs.recommended_parts.map((r, i) => (
                      <tr key={i}>
                        <td style={{ color: "var(--text-muted)" }}>
                          {r.category}
                        </td>
                        <td className="td-model">
                          {displayName(r.brand, r.model)}
                        </td>
                        <td
                          style={{
                            fontSize: 11,
                            color: "var(--text-muted)",
                            maxWidth: 300,
                          }}
                        >
                          {r.reasoning}
                        </td>
                        <td
                          className="td-price"
                          style={{ textAlign: "right" }}
                        >
                          {sym}{fmt(r.price_usd, currency)}
                        </td>
                        <td>
                          <span
                            style={{
                              fontSize: 11,
                              fontWeight: 700,
                              color:
                                r.compatibility_score >= 0.9
                                  ? "var(--green)"
                                  : r.compatibility_score >= 0.7
                                  ? "var(--amber)"
                                  : "var(--red)",
                            }}
                          >
                            {Math.round(r.compatibility_score * 100)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Alternatives */}
            {Object.keys(recs.alternatives).length > 0 && (
              <div className="panel">
                <div className="panel-header">
                  <span className="panel-title">Alternative Options</span>
                </div>
                <div className="table-wrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Category</th>
                        <th>Model</th>
                        <th>Notes</th>
                        <th style={{ textAlign: "right" }}>Price</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(recs.alternatives).flatMap(
                        ([cat, alts]) =>
                          alts.map((alt, i) => (
                            <tr key={`${cat}-${i}`}>
                              <td style={{ color: "var(--text-muted)" }}>
                                {cat}
                              </td>
                              <td className="td-model">
                                {displayName(alt.brand, alt.model)}
                              </td>
                              <td
                                style={{
                                  fontSize: 11,
                                  color: "var(--text-muted)",
                                }}
                              >
                                {alt.notes}
                              </td>
                              <td
                                className="td-price"
                                style={{ textAlign: "right" }}
                              >
                                {sym}{fmt(alt.price_usd, currency)}
                              </td>
                            </tr>
                          ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}

        {/* ── NOTES ──────────────────────────────────────────── */}
        {activeTab === "notes" && (
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title">System Notes</span>
              <span className="badge badge-gray">{data.notes.length}</span>
            </div>
            <div className="panel-body">
              {data.notes.length === 0 ? (
                <p style={{ color: "var(--text-muted)", fontSize: 12 }}>
                  No additional notes for this build.
                </p>
              ) : (
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 8 }}
                  className="stagger"
                >
                  {data.notes.map((note, i) => (
                    <div
                      key={i}
                      className="alert alert-info animate-fade-in"
                    >
                      <span style={{ color: "var(--red)", flexShrink: 0 }}>
                        //
                      </span>
                      <span style={{ fontSize: 12 }}>{note}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Spacer for export bar */}
        <div style={{ height: 72 }} />
      </div>

      {/* ── Sticky export bar ─────────────────────────────────── */}
      <div className="export-bar">
        <div className="export-bar-info">
          <strong>{sym}{fmt(summary.total_combined_usd, currency)}</strong> ·{" "}
          {data.pricing.length} components ·{" "}
          Build{" "}
          <strong style={{ color: "var(--red)" }}>
            {data.build_id.slice(0, 8).toUpperCase()}
          </strong>
        </div>
        <div className="export-bar-actions">
          <Link href="/builder" className="btn btn-ghost btn-sm">
            ← New Build
          </Link>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleCSV}
            disabled={exporting === "csv"}
          >
            {exporting === "csv" ? (
              <span className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} />
            ) : null}
            ↓ CSV
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleExcel}
            disabled={exporting === "excel"}
          >
            {exporting === "excel" ? (
              <span className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} />
            ) : null}
            ↓ Excel
          </button>
        </div>
      </div>
    </div>
  );
}
