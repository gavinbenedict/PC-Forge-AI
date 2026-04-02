/**
 * PCForge AI — Typed API client
 * All communication with the FastAPI backend.
 */

// 🔥 FINAL FIX — HARDCODE YOUR RAILWAY BACKEND
const API_BASE = "https://pc-forge-ai-production.up.railway.app/api/v1";

export interface RAMSpec {
  size_gb?: number;
  type?: string;
  speed_mhz?: number;
  modules?: number;
}

export interface StorageSpec {
  type?: string;
  capacity_gb?: number;
  interface?: string;
}

export interface BuildSpec {
  cpu?: string;
  gpu?: string;
  motherboard?: string;
  ram?: RAMSpec;
  storage?: StorageSpec[];
  psu?: string;
  case?: string;
  cooler?: string;
  monitor?: string;
  budget_usd?: number;
  preferred_brand?: string;
  usage_type?: "gaming" | "streaming" | "editing" | "workstation" | "mixed" | "office";
  region?: "US" | "EU" | "UK" | "IN" | "CA" | "AU";
}

export interface CompatibilityIssue {
  severity: "error" | "warning" | "info";
  component: string;
  issue: string;
  suggested_fix: string;
}

export interface CompatibilityReport {
  status: "valid" | "warning" | "invalid";
  issues: CompatibilityIssue[];
  passed_checks: string[];
  total_checks: number;
}

export interface PriceRange {
  min_price: number;
  average_price: number;
  max_price: number;
}

export interface PricedPart {
  category: string;
  brand: string;
  model: string;
  price_usd: number;
  currency: string;
  store: string;
  availability: string;
  url: string;
  last_updated: string;
  source: "live" | "simulated" | "predicted";
  predicted_range?: PriceRange;
}

export interface RecommendedPart {
  category: string;
  model: string;
  brand: string;
  reasoning: string;
  price_usd: number;
  compatibility_score: number;
  is_auto_filled: boolean;
}

export interface AlternativeOption {
  model: string;
  brand: string;
  price_usd: number;
  notes: string;
}

export interface RecommendationResult {
  recommended_parts: RecommendedPart[];
  alternatives: Record<string, AlternativeOption[]>;
  inferred_tier: "budget" | "mid-range" | "high-end" | "enthusiast";
  tier_reasoning: string;
}

export interface ResolvedComponent {
  category: string;
  brand: string;
  model: string;
  specs: Record<string, unknown>;
  is_auto_filled: boolean;
}

export interface PriceSummary {
  total_live_usd: number;
  total_predicted_usd: number;
  total_combined_usd: number;
  market_range: PriceRange;
  live_parts_count: number;
  predicted_parts_count: number;
  currency: string;
  region: string;
}

export interface AnalyzeResponse {
  build_id: string;
  timestamp: string;
  original_input: Record<string, unknown>;
  completed_build: ResolvedComponent[];
  auto_filled_components: string[];
  compatibility: CompatibilityReport;
  recommendations: RecommendationResult;
  pricing: PricedPart[];
  price_summary: PriceSummary;
  notes: string[];
  inferred_tier: "budget" | "mid-range" | "high-end" | "enthusiast";
  usage_type?: string;
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export async function analyzeBuild(spec: BuildSpec): Promise<AnalyzeResponse> {
  return apiFetch<AnalyzeResponse>("/analyze-build", {
    method: "POST",
    body: JSON.stringify(spec),
  });
}

export async function exportExcel(analysis: AnalyzeResponse): Promise<Blob> {
  const res = await fetch(`${API_BASE}/export/excel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(analysis),
  });

  if (!res.ok) throw new Error("Excel export failed");

  return res.blob();
}

export async function exportCSV(analysis: AnalyzeResponse): Promise<Blob> {
  const res = await fetch(`${API_BASE}/export/csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(analysis),
  });

  if (!res.ok) throw new Error("CSV export failed");

  return res.blob();
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}