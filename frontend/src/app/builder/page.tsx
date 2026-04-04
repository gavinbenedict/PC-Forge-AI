"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ParticleCanvas from "@/components/ParticleCanvas";
import { analyzeBuild, type BuildSpec } from "@/lib/api";

// ─── Step definitions ─────────────────────────────────────────────────────────

const STEPS = [
  { id: 1, label: "Usage & Budget" },
  { id: 2, label: "CPU & GPU" },
  { id: 3, label: "Motherboard & RAM" },
  { id: 4, label: "Storage & Cooling" },
  { id: 5, label: "Review & Analyse" },
];

// ─── Option lists ─────────────────────────────────────────────────────────────

const USAGE_TYPES = [
  { value: "gaming",      label: "Gaming" },
  { value: "streaming",   label: "Streaming" },
  { value: "editing",     label: "Editing / Content Creation" },
  { value: "workstation", label: "Workstation / 3D / Rendering" },
  { value: "mixed",       label: "Mixed Use" },
  { value: "office",      label: "Office / Light Tasks" },
];

const REGIONS = [
  { value: "US", label: "United States (USD)" },
  { value: "EU", label: "Europe (EUR equivalent)" },
  { value: "UK", label: "United Kingdom (GBP equiv.)" },
  { value: "CA", label: "Canada (CAD equiv.)" },
  { value: "AU", label: "Australia (AUD equiv.)" },
  { value: "IN", label: "India (USD equiv.)" },
];

const RAM_TYPES   = ["DDR4", "DDR5"];
const RAM_SIZES   = [8, 16, 32, 64, 128];
const RAM_SPEEDS  = {
  DDR4: [2400, 2666, 3000, 3200, 3600, 4000, 4266],
  DDR5: [4800, 5200, 5600, 6000, 6400, 7200, 8000],
};

const STORAGE_TYPES = [
  { value: "NVMe Gen3",  label: "NVMe Gen 3 (M.2)" },
  { value: "NVMe Gen4",  label: "NVMe Gen 4 (M.2)" },
  { value: "NVMe Gen5",  label: "NVMe Gen 5 (M.2)" },
  { value: "SATA SSD",   label: "SATA SSD (2.5\")" },
  { value: "HDD",        label: "HDD (3.5\")" },
];

const STORAGE_CAPACITIES = [
  { value: 256,  label: "256 GB" },
  { value: 512,  label: "512 GB" },
  { value: 1024, label: "1 TB" },
  { value: 2048, label: "2 TB" },
  { value: 4096, label: "4 TB" },
];

// ─── Step progress indicator ──────────────────────────────────────────────────

function StepIndicator({
  steps,
  current,
}: {
  steps: typeof STEPS;
  current: number;
}) {
  return (
    <div className="step-indicator" style={{ gap: 0 }}>
      {steps.map((s, i) => (
        <div key={s.id} style={{ display: "flex", alignItems: "center" }}>
          <div
            className={`step-item ${
              current === s.id
                ? "active"
                : current > s.id
                ? "done"
                : ""
            }`}
            style={{ display: "flex", alignItems: "center", gap: 8 }}
          >
            <div
              className={`step-num ${
                current === s.id ? "active" : current > s.id ? "done" : ""
              }`}
            >
              {current > s.id ? "\u2713" : String(s.id).padStart(2, "0")}
            </div>
            {/* Label: always visible on active, hidden on inactive via CSS media query */}
            <span
              className={`step-label ${
                current !== s.id ? "step-label-inactive" : ""
              }`}
            >
              {s.label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div
              className={`step-connector ${
                current > s.id ? "done" : current === s.id ? "active" : ""
              }`}
              style={{ margin: "0 8px" }}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Section wrapper ──────────────────────────────────────────────────────────

function FieldSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="builder-section animate-fade-in">
      <div className="section-title">{title}</div>
      {children}
    </div>
  );
}

// ─── Main builder component ───────────────────────────────────────────────────

export default function BuilderPage() {
  const router = useRouter();

  // Form state — initialised from localStorage so back-navigation restores the form
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Restore form state from localStorage ───────────────────────
  const _ls = (key: string, fallback: string) => {
    if (typeof window === "undefined") return fallback;
    return localStorage.getItem(`pcforge_builder_${key}`) ?? fallback;
  };
  const _lsNum = (key: string, fallback: number) => {
    const v = _ls(key, String(fallback));
    const n = parseFloat(v);
    return isNaN(n) ? fallback : n;
  };

  // Step 1 — Usage
  const [usageType, setUsageType] = useState<string>(() => _ls("usageType", ""));
  const [budgetUsd, setBudgetUsd] = useState<string>(() => _ls("budgetUsd", ""));
  const [region, setRegion] = useState(() => _ls("region", "US"));
  const [preferredBrand, setPreferredBrand] = useState(() => _ls("preferredBrand", ""));

  // Step 2 — CPU + GPU
  const [cpu, setCpu] = useState(() => _ls("cpu", ""));
  const [gpu, setGpu] = useState(() => _ls("gpu", ""));

  // Step 3 — MB + RAM
  const [motherboard, setMotherboard] = useState(() => _ls("motherboard", ""));
  const [ramType, setRamType] = useState(() => _ls("ramType", "DDR5"));
  const [ramSizeGb, setRamSizeGb] = useState<number>(() => _lsNum("ramSizeGb", 32));
  const [ramSpeedMhz, setRamSpeedMhz] = useState<number>(() => _lsNum("ramSpeedMhz", 6000));
  const [ramModules, setRamModules] = useState<number>(() => _lsNum("ramModules", 2));

  // Step 4 — Storage + Cooling
  const [storageType, setStorageType] = useState(() => _ls("storageType", "NVMe Gen4"));
  const [storageCapacityGb, setStorageCapacityGb] = useState<number>(() => _lsNum("storageCapacityGb", 1024));
  const [psu, setPsu] = useState(() => _ls("psu", ""));
  const [caseName, setCaseName] = useState(() => _ls("caseName", ""));
  const [cooler, setCooler] = useState(() => _ls("cooler", ""));

  // ── Persist every change to localStorage ───────────────────────
  useEffect(() => {
    const save = (k: string, v: string | number) =>
      localStorage.setItem(`pcforge_builder_${k}`, String(v));
    save("usageType", usageType);
    save("budgetUsd", budgetUsd);
    save("region", region);
    save("preferredBrand", preferredBrand);
    save("cpu", cpu);
    save("gpu", gpu);
    save("motherboard", motherboard);
    save("ramType", ramType);
    save("ramSizeGb", ramSizeGb);
    save("ramSpeedMhz", ramSpeedMhz);
    save("ramModules", ramModules);
    save("storageType", storageType);
    save("storageCapacityGb", storageCapacityGb);
    save("psu", psu);
    save("caseName", caseName);
    save("cooler", cooler);
  }, [
    usageType, budgetUsd, region, preferredBrand,
    cpu, gpu, motherboard,
    ramType, ramSizeGb, ramSpeedMhz, ramModules,
    storageType, storageCapacityGb, psu, caseName, cooler,
  ]);

  // ── Navigation helpers ──────────────────────────────────────────
  const canAdvance = (): boolean => {
    if (step === 1) {
      return !!usageType; // At minimum a usage type is required
    }
    return true; // All other steps allow skipping
  };

  const next = () => step < 5 && setStep((s) => s + 1);
  const prev = () => step > 1 && setStep((s) => s - 1);

  // ── Submit ──────────────────────────────────────────────────────
  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    const spec: BuildSpec = {
      usage_type: usageType as BuildSpec["usage_type"] || undefined,
      region:     region as BuildSpec["region"],
      budget_usd: budgetUsd ? parseFloat(budgetUsd) : undefined,
      preferred_brand: preferredBrand || undefined,
      cpu:         cpu || undefined,
      gpu:         gpu || undefined,
      motherboard: motherboard || undefined,
      ram: {
        type:      ramType,
        size_gb:   ramSizeGb,
        speed_mhz: ramSpeedMhz,
        modules:   ramModules,
      },
      storage: [
        {
          type:        storageType,
          capacity_gb: storageCapacityGb,
          interface:   storageType,
        },
      ],
      psu:    psu || undefined,
      case:   caseName || undefined,
      cooler: cooler || undefined,
    };

    try {
      const result = await analyzeBuild(spec);
      // Store result in sessionStorage and navigate
      sessionStorage.setItem("pcforge_result", JSON.stringify(result));
      router.push("/results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  // ── Speed options for current RAM type ────────────────────────
  const speedOptions =
    RAM_SPEEDS[ramType as keyof typeof RAM_SPEEDS] || RAM_SPEEDS["DDR5"];

  // ────────────────────────────────────────────────────────────────────────────

  return (
    <div className="builder-layout">
      <ParticleCanvas />

      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="builder-header content-layer">
        <div className="container" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Top row */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 16,
            }}
          >
            <div>
              <p
                style={{
                  fontSize: 9,
                  fontWeight: 700,
                  letterSpacing: "0.2em",
                  textTransform: "uppercase",
                  color: "var(--red)",
                  marginBottom: 4,
                }}
              >
                // BUILD CONFIGURATION
              </p>
              <h1
                style={{
                  fontSize: 22,
                  fontWeight: 800,
                  letterSpacing: "-0.02em",
                }}
              >
                PC Build Analyser
              </h1>
            </div>
            <Link href="/" className="btn btn-ghost btn-sm">
              ← Home
            </Link>
          </div>

          {/* Step indicator */}
          <StepIndicator steps={STEPS} current={step} />
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${(step / STEPS.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* ── Form body ──────────────────────────────────────────── */}
      <div className="builder-body content-layer">
        {error && (
          <div className="alert alert-error animate-fade-in" style={{ marginBottom: 24 }}>
            <span>⚠</span>
            <span>{error}</span>
          </div>
        )}

        {/* ── STEP 1: Usage & Budget ─────────────────────────── */}
        {step === 1 && (
          <>
            <FieldSection title="Usage Profile">
              <div className="component-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))" }}>
                {USAGE_TYPES.map((u) => (
                  <button
                    key={u.value}
                    onClick={() => setUsageType(u.value)}
                    style={{
                      background:
                        usageType === u.value ? "var(--red-dim)" : "var(--bg-card)",
                      border: `1px solid ${
                        usageType === u.value ? "var(--red-border)" : "var(--border)"
                      }`,
                      color:
                        usageType === u.value
                          ? "var(--text-primary)"
                          : "var(--text-secondary)",
                      padding: "14px 16px",
                      borderRadius: "var(--r-md)",
                      cursor: "pointer",
                      textAlign: "left",
                      fontFamily: "var(--font)",
                      fontSize: 12,
                      fontWeight: usageType === u.value ? 700 : 400,
                      transition: "all var(--t-base)",
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                    }}
                  >
                    {usageType === u.value && (
                      <span style={{ color: "var(--red)" }}>▸</span>
                    )}
                    {u.label}
                  </button>
                ))}
              </div>
            </FieldSection>

            <FieldSection title="Budget & Region">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Total Budget (USD)</label>
                  <div className="input-group">
                    <span className="input-prefix">$</span>
                    <input
                      type="number"
                      className="form-input"
                      placeholder="e.g. 1500"
                      value={budgetUsd}
                      onChange={(e) => setBudgetUsd(e.target.value)}
                      min={0}
                    />
                  </div>
                  <p className="form-hint">Leave empty for no budget constraint</p>
                </div>

                <div className="form-group">
                  <label className="form-label">Region</label>
                  <select
                    className="form-select"
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                  >
                    {REGIONS.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                  <label className="form-label">Preferred Brand (optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. ASUS, Corsair, Samsung"
                    value={preferredBrand}
                    onChange={(e) => setPreferredBrand(e.target.value)}
                  />
                </div>
              </div>
            </FieldSection>
          </>
        )}

        {/* ── STEP 2: CPU & GPU ──────────────────────────────── */}
        {step === 2 && (
          <>
            <div
              className="alert alert-info animate-fade-in"
              style={{ marginBottom: 24 }}
            >
              <span>ℹ</span>
              <span>
                Fields are optional — leave blank to let the AI auto-fill based
                on your usage profile and budget.
              </span>
            </div>

            <FieldSection title="Processor (CPU)">
              <div className="form-group">
                <label className="form-label">CPU Model</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Intel Core i7-13700K, AMD Ryzen 9 7950X"
                  value={cpu}
                  onChange={(e) => setCpu(e.target.value)}
                />
                <p className="form-hint">
                  Enter exact model name for best compatibility checking
                </p>
              </div>
            </FieldSection>

            <FieldSection title="Graphics Card (GPU)">
              <div className="form-group">
                <label className="form-label">GPU Model</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. NVIDIA RTX 4080 Super, AMD Radeon RX 7900 XTX"
                  value={gpu}
                  onChange={(e) => setGpu(e.target.value)}
                />
                <p className="form-hint">
                  Include brand prefix for accurate pricing and compatibility
                </p>
              </div>
            </FieldSection>
          </>
        )}

        {/* ── STEP 3: Motherboard & RAM ──────────────────────── */}
        {step === 3 && (
          <>
            <FieldSection title="Motherboard">
              <div className="form-group">
                <label className="form-label">Motherboard Model</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. ASUS ROG Strix Z790-E Gaming, MSI MAG B650 Tomahawk"
                  value={motherboard}
                  onChange={(e) => setMotherboard(e.target.value)}
                />
                <p className="form-hint">
                  Will be auto-selected based on CPU socket if left blank
                </p>
              </div>
            </FieldSection>

            <FieldSection title="RAM / Memory">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                  gap: 12,
                }}
              >
                <div className="form-group">
                  <label className="form-label">Memory Type</label>
                  <select
                    className="form-select"
                    value={ramType}
                    onChange={(e) => {
                      setRamType(e.target.value);
                      const speeds =
                        RAM_SPEEDS[e.target.value as keyof typeof RAM_SPEEDS];
                      setRamSpeedMhz(speeds[Math.floor(speeds.length / 2)]);
                    }}
                  >
                    {RAM_TYPES.map((t) => (
                      <option key={t}>{t}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Capacity (GB)</label>
                  <select
                    className="form-select"
                    value={ramSizeGb}
                    onChange={(e) => setRamSizeGb(Number(e.target.value))}
                  >
                    {RAM_SIZES.map((s) => (
                      <option key={s} value={s}>
                        {s} GB
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Speed (MHz)</label>
                  <select
                    className="form-select"
                    value={ramSpeedMhz}
                    onChange={(e) => setRamSpeedMhz(Number(e.target.value))}
                  >
                    {speedOptions.map((s) => (
                      <option key={s} value={s}>
                        {s} MHz
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Modules</label>
                  <select
                    className="form-select"
                    value={ramModules}
                    onChange={(e) => setRamModules(Number(e.target.value))}
                  >
                    {[1, 2, 4].map((m) => (
                      <option key={m} value={m}>
                        {m}× {ramSizeGb / m} GB
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </FieldSection>
          </>
        )}

        {/* ── STEP 4: Storage & Cooling ──────────────────────── */}
        {step === 4 && (
          <>
            <FieldSection title="Primary Storage">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Interface / Type</label>
                  <select
                    className="form-select"
                    value={storageType}
                    onChange={(e) => setStorageType(e.target.value)}
                  >
                    {STORAGE_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Capacity</label>
                  <select
                    className="form-select"
                    value={storageCapacityGb}
                    onChange={(e) =>
                      setStorageCapacityGb(Number(e.target.value))
                    }
                  >
                    {STORAGE_CAPACITIES.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </FieldSection>

            <FieldSection title="Power, Case & Cooling (optional)">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Power Supply (PSU)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Corsair RM850x 850W 80+ Gold"
                    value={psu}
                    onChange={(e) => setPsu(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Case / Chassis</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Lian Li PC-O11 Dynamic EVO"
                    value={caseName}
                    onChange={(e) => setCaseName(e.target.value)}
                  />
                </div>

                <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                  <label className="form-label">CPU Cooler</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Noctua NH-D15, Corsair iCUE H150i Elite"
                    value={cooler}
                    onChange={(e) => setCooler(e.target.value)}
                  />
                </div>
              </div>
            </FieldSection>
          </>
        )}

        {/* ── STEP 5: Review & Submit ─────────────────────────── */}
        {step === 5 && (
          <>
            <FieldSection title="Build Summary">
              <div
                className="panel"
                style={{ marginBottom: 16 }}
              >
                <div className="panel-header">
                  <span className="panel-title">Configuration</span>
                  <span
                    style={{
                      fontSize: 10,
                      color: "var(--text-muted)",
                    }}
                  >
                    Auto-fill active for blank fields
                  </span>
                </div>
                <div className="panel-body">
                  <table className="table" style={{ fontSize: 12 }}>
                    <tbody>
                      {[
                        ["Usage Type",  usageType || "—"],
                        ["Region",      region],
                        ["Budget",      budgetUsd ? `$${budgetUsd}` : "No limit"],
                        ["Pref. Brand", preferredBrand || "Any"],
                        ["CPU",         cpu || "⚙ Auto-fill"],
                        ["GPU",         gpu || "⚙ Auto-fill"],
                        ["Motherboard", motherboard || "⚙ Auto-fill"],
                        ["RAM",         `${ramType} ${ramSizeGb}GB @ ${ramSpeedMhz}MHz`],
                        ["Storage",     `${storageType} — ${storageCapacityGb >= 1024 ? `${storageCapacityGb/1024}TB` : `${storageCapacityGb}GB`}`],
                        ["PSU",         psu || "⚙ Auto-fill"],
                        ["Case",        caseName || "⚙ Auto-fill"],
                        ["Cooler",      cooler || "⚙ Auto-fill"],
                      ].map(([k, v]) => (
                        <tr key={k}>
                          <td
                            style={{
                              color: "var(--text-muted)",
                              width: 160,
                              fontWeight: 600,
                              fontSize: 10,
                              letterSpacing: "0.08em",
                              textTransform: "uppercase",
                            }}
                          >
                            {k}
                          </td>
                          <td
                            style={{
                              color: v.startsWith("⚙")
                                ? "var(--amber)"
                                : "var(--text-primary)",
                            }}
                          >
                            {v}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="alert alert-info">
                <span>ℹ</span>
                <span>
                  Fields marked{" "}
                  <strong style={{ color: "var(--amber)" }}>⚙ Auto-fill</strong>{" "}
                  will be intelligently selected by the AI recommendation engine
                  based on your usage profile, budget, and hardware compatibility.
                </span>
              </div>
            </FieldSection>
          </>
        )}

        {/* ── Navigation buttons ──────────────────────────────── */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 32,
            paddingTop: 24,
            borderTop: "1px solid var(--border)",
          }}
        >
          <button
            className="btn btn-secondary"
            onClick={prev}
            disabled={step === 1}
          >
            ← Back
          </button>

          <span
            style={{
              fontSize: 10,
              color: "var(--text-muted)",
              letterSpacing: "0.12em",
              fontWeight: 600,
              textTransform: "uppercase",
            }}
          >
            Step {step} / {STEPS.length}
          </span>

          {step < 5 ? (
            <button
              className="btn btn-primary"
              onClick={next}
              disabled={!canAdvance()}
            >
              Next →
            </button>
          ) : (
            <button
              className="btn btn-cta"
              onClick={handleSubmit}
              disabled={loading}
              style={{ minWidth: 160 }}
            >
              {loading ? (
                <>
                  <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                  Analysing
                  <span className="loading-dots" />
                </>
              ) : (
                "> Analyse Build"
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
