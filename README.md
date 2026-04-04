

# PCForge AI

> Intelligent PC Build Analysis · Strict Compatibility · Real-time Pricing · Global Currency

PCForge AI accepts partial or complete PC build specifications, validates component compatibility, auto-fills missing parts from a dataset-driven master catalogue, estimates market pricing, and returns a structured report — all in a single API request.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Why PCForge AI?](#why-pcforge-ai)
3. [Overview](#overview)
4. [Architecture](#architecture)
5. [Features](#features)
6. [Setup](#setup)
7. [Usage](#usage)
8. [System Design](#system-design)
9. [Limitations](#limitations)
10. [Future Improvements](#future-improvements)
11. [Project Structure](#project-structure)
12. [Demo](#demo)

---

## Quick Start

Get PCForge AI running locally in under two minutes.

**1. Start the Backend (Terminal 1)**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000
```

**2. Start the Frontend (Terminal 2)**
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local
npm run dev
```
Open **http://localhost:3000** in your browser.

---

## Why PCForge AI?

Building a PC requires navigating thousands of components, complex compatibility rules, and fluctuating regional pricing. PCForge AI removes this friction by instantly turning partial ideas (e.g., "I want an RTX 4090") into complete, strictly validated, and budget-balanced builds. It proactively prevents physical bottlenecks, calculates exact power requirements, and standardizes hardware data across global currencies.

---

## Overview

| Capability | Details |
|---|---|
| Accepts partial builds | GPU only, CPU only, or any combination |
| Auto-fills missing components | Tier-aware: budget / mid-range / high-end / enthusiast |
| Validates compatibility | 8 rules: socket, RAM type, PSU load, clearances |
| Prices every component | Simulated market prices ±3% jitter; XGBoost ML fallback |
| Multi-currency output | USD · EUR · GBP · CAD · AUD · INR |
| Exports full reports | Excel (6 sheets) or flat CSV |

**Catalogue:** 542 components · 8 categories · 6 currencies · R²=0.9755 ML model

---

## Architecture

```
┌──────────────────────────────────────────────┐
│              Next.js Frontend                │
│  /builder  → build input form                │
│  /results  → tabbed report                   │
└───────────────────┬──────────────────────────┘
                    │  POST /api/v1/analyze-build
                    ▼
┌──────────────────────────────────────────────┐
│              FastAPI Backend                 │
│                                              │
│  routes/analyze.py       (orchestrator)      │
│    ├─ normalize_build_spec                   │
│    ├─ MasterCatalogue.resolve_user_component │
│    ├─ run_recommendations                    │
│    ├─ run_compatibility_check                │
│    ├─ pricing_service  → ML fallback         │
│    └─ fx_convert  (currency layer)           │
│                                              │
│  data/preprocessor.py ← pc_parts.json        │
└──────────────────────────────────────────────┘
```

### Data Flow

```
BuildSpec (user input)
  1. Normalize   → clean names, parse budget/region
  2. Resolve     → Exact → Norm-exact → Substring → Token-overlap
                   Critical token mismatch = HARD BLOCK
  3. Recommend   → fill all 8 missing categories (GPU priority first)
  4. Validate    → 8 compat rules; surface errors/warnings
  5. Price       → Catalogue → _PRICE_DB → XGBoost ML
  6. Convert     → region → currency → fx_convert()
  7. Return      → AnalyzeResponse
```

---

## Features

### Strict Component Matching

| Step | Method | Guard |
|---|---|---|
| 1 | Exact (case-insensitive) | Full string |
| 2 | Normalised exact | Strip [^a-z0-9] |
| 3 | Substring | Query IN candidate; critical tokens must match |
| 4 | Token-overlap ≥ 0.75 | Critical mismatch = hard skip |

9600X will NEVER match 7600X. B650 will NEVER match Z790.
All substitutions surface is_substitution=True with a warning message.

### Compatibility Engine (8 Rules)

| Rule | Check |
|---|---|
| CPU / Motherboard socket | AM5/AM4/LGA1700 must match |
| RAM type / Motherboard | DDR4/DDR5 must match |
| PSU headroom | (CPU TDP + GPU TDP + 100W) × 1.30 ≤ PSU wattage |
| Case form factor | ATX/mATX/ITX ↔ case supported formats |
| GPU clearance | GPU length ≤ case GPU clearance |
| Cooler height | Cooler height ≤ case cooler clearance |
| Storage interface | NVMe/SATA ↔ motherboard slots |
| RAM capacity | Total RAM ≤ motherboard max RAM |

### Recommendation Engine

- Tier inference: GPU signal > CPU signal > budget signal > usage type
- Covers Ryzen 9000 (9600–9950X), Ryzen 7000, Intel 12/13/14th Gen
- GPU catalogue: RTX 4060–5090, RX 7600–9070 XT
- All 8 categories always filled — no exceptions
- 2–3 diversified alternatives per category (brand rotation)

### Hybrid Pricing

```
1. MasterCatalogue base price  → +/- 3% jitter
2. _PRICE_DB exact lookup      → ~300 hardcoded SKUs
3. _PRICE_DB strict-token match → all numeric tokens must match
4. XGBoost ML prediction       → trained on cores/VRAM/TDP/category
```

### Currency Conversion

| Region | Currency |
|---|---|
| US | USD |
| EU | EUR |
| UK | GBP |
| CA | CAD |
| AU | AUD |
| IN | INR |

Applied to all PricedPart prices, all summary totals, and all notes.

---

## Setup

Follow these detailed instructions to set up the development environment from scratch.

### Prerequisites

Before beginning, ensure you have the following installed on your system:
- Python 3.10+ (Required for the backend API and ML models)
- Node.js 18+ (Required for the Next.js frontend)
- macOS: `brew install libomp` (Required for XGBoost ML model)

### Backend

The backend is built with FastAPI and runs on Python. To avoid conflicting dependencies, we recommend using a virtual environment.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000
```

- API: http://localhost:8000/api/v1
- Docs: http://localhost:8000/docs

### Frontend

The frontend is a modern Next.js web application.

```bash
cd frontend
npm install
npm run dev
```

- UI: http://localhost:3000

### Environment

For the frontend to successfully communicate with the backend API, you must configure its environment variables.

Create a file named `frontend/.env.local` and add the following:

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## Usage

### POST /api/v1/analyze-build

```json
{
  "cpu":        "AMD Ryzen 9 9950X",
  "gpu":        "NVIDIA GeForce RTX 5090",
  "usage_type": "workstation",
  "budget_usd": 5000,
  "region":     "US"
}
```

All fields optional — provide at least one component or a budget.

### Example Response (abbreviated)

```json
{
  "inferred_tier": "enthusiast",
  "completed_build": [
    { "category": "CPU",  "model": "AMD Ryzen 9 9950X",                   "is_auto_filled": false },
    { "category": "GPU",  "model": "ASUS GeForce RTX 5090 TUF Gaming OC", "is_auto_filled": false },
    { "category": "RAM",  "model": "G.Skill Trident Z5 DDR5-6400 32GB",   "is_auto_filled": true  }
  ],
  "price_summary": {
    "total_combined_usd": 4210.50,
    "currency": "USD",
    "market_range": { "min_price": 3705.24, "max_price": 4968.39 }
  },
  "compatibility": {
    "status": "valid",
    "issues": []
  }
}
```

### Partial Input

```json
{ "gpu": "NVIDIA GeForce RTX 4070", "usage_type": "gaming", "region": "IN" }
```

All 8 categories auto-filled · priced in INR · tier = mid-range

---

## System Design

### Matching Algorithm

```
resolve_user_component(name, category, threshold=0.75)

  Step 1: self._name_index.get(name.lower())
  Step 2: normalise([^a-z0-9] stripped) == normalise(key)
  Step 3: name.lower() in cand.full_name.lower()
            AND query_critical_tokens <= cand_critical_tokens
  Step 4: token_score(query, cand) >= 0.75
            critical token mismatch → continue (hard skip, not penalty)
```

### Recommendation Priority

```
GPU → CPU → Motherboard → RAM → Storage → PSU → Case → Cooler

For each missing slot:
  candidates = filter(tier == inferred AND usage in uses)
  fallback:  relax usage → relax tier
  output:    primary + 2 alternatives (different brands)
```

### Pricing Resolution

```
get_price(model, category)
  1. MasterCatalogue.find_by_name()  → base_price ± 3% jitter
  2. _PRICE_DB[model]                → exact key
  3. _PRICE_DB partial               → numeric tokens must all match
  4. prediction_service.predict()    → XGBoost ML
```

---

## Limitations

- No live prices — all pricing is simulated. Do not purchase based on output alone.
- Static FX rates — currency rates are hardcoded approximates, not live.
- Dataset-dependent — unknown components fall back to ML; accuracy varies.
- XGBoost requires libomp on macOS: brew install libomp
- No persistence — builds are not saved between sessions.
- Substitution risk — is_substitution=True means the matched part may differ from intent.

---

## Future Improvements

| Area | Enhancement |
|---|---|
| Pricing | Live APIs: Newegg, Amazon PA, PCPartPicker |
| Currency | Live FX via frankfurter.app |
| ML Model | Retrain on 2024–2025 data; add benchmark scores |
| Recommendations | LLM-assisted per-slot reasoning |
| User Accounts | Save, share, version builds |
| Dataset | Automated scrape-and-refresh pipeline |
| UI | Real-time compat feedback, drag-and-drop builder |
| Performance | Redis caching, async parallel price lookups |

---

## Project Structure

```
PC Forge Ai/
├── backend/
│   ├── app.py                         # FastAPI entry, catalogue loaded on startup
│   ├── data/
│   │   ├── catalogue.py               # MasterCatalogue singleton + resolver
│   │   ├── preprocessor.py            # filter / normalise / dedup / expand
│   │   └── raw_schema.py              # Field aliases + required fields
│   ├── models/schemas.py              # Pydantic models
│   ├── routes/
│   │   ├── analyze.py                 # POST /analyze-build
│   │   └── export.py                  # GET /export/excel, /export/csv
│   ├── services/
│   │   ├── compatibility_service.py
│   │   ├── pricing_service.py
│   │   ├── prediction_service.py      # XGBoost ML fallback
│   │   └── recommendation_service.py
│   └── utils/
│       ├── currency.py                # FX conversion
│       ├── exporter.py                # Excel/CSV export
│       └── normalizer.py             # Input cleaning
├── data/raw/pc_parts.json             # 542-component master dataset
├── frontend/src/
│   ├── app/
│   │   ├── builder/page.tsx           # Build input form
│   │   └── results/page.tsx           # Tabbed results report
│   └── lib/api.ts                     # Typed API client
├── requirements.txt
└── README.md
```

---

PCForge AI v2.0 — Dataset-Driven · Strict Matching · Full Compatibility · Multi-Currency
