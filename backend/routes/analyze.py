"""
PCForge AI — /analyze-build Route
Orchestrates all services to produce a full build analysis.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.models.schemas import (
    AnalyzeResponse,
    BuildSpec,
    PricedPart,
    PriceRange,
    PriceSummary,
    ResolvedComponent,
)
from backend.services.compatibility_service import run_compatibility_check
from backend.services.pricing_service import pricing_service
from backend.services.prediction_service import prediction_service
from backend.services.recommendation_service import run_recommendations
from backend.utils.normalizer import normalize_build_spec
from backend.utils.currency import convert as fx_convert, symbol as fx_symbol, SUPPORTED_CURRENCIES

# ✅ ADDED THIS IMPORT
from backend.data.catalogue import master_catalogue

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Component resolution helpers ─────────────────────────────────────────────

def _extract_brand(model_name: str) -> str:
    brands = [
        "AMD", "Intel", "NVIDIA", "ASUS", "MSI", "Gigabyte", "ASRock",
        "Corsair", "G.Skill", "Kingston", "Samsung", "WD", "Seagate",
        "Crucial", "Noctua", "be quiet!", "Lian Li", "Fractal", "NZXT",
        "Seasonic", "EVGA", "Cooler Master", "DeepCool", "Thermalright",
        "ARCTIC", "ID-COOLING", "Thermaltake", "Phanteks", "Antec",
        "Silverstone", "Teamgroup", "LG", "Dell", "BenQ", "AOC",
    ]
    for brand in brands:
        if model_name.startswith(brand):
            return brand
    return model_name.split()[0] if model_name else "Unknown"


def _resolve_component(
    category: str,
    model_name: Optional[str],
    brand: Optional[str] = None,
    is_auto_filled: bool = False,
    specs: Optional[Dict[str, Any]] = None,
) -> Optional[ResolvedComponent]:
    if not model_name:
        return None
    brand = brand or _extract_brand(model_name)
    return ResolvedComponent(
        category=category,
        brand=brand,
        model=model_name,
        specs=specs or {},
        is_auto_filled=is_auto_filled,
    )


def _price_or_predict(
    model_name: str,
    category: str,
    brand: str,
    tier: str,
    usage_type: Optional[str],
    specs: Optional[Dict[str, Any]] = None,
) -> PricedPart:
    priced = pricing_service.get_price(model_name, category)
    if priced:
        return priced
    return prediction_service.build_priced_part_predicted(
        category=category,
        brand=brand,
        model_name=model_name,
        tier=tier,
        usage_type=usage_type,
        specs=specs or {},
    )


# ─── Main Analysis Route ──────────────────────────────────────────────────────

@router.post("/analyze-build", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_build(spec: BuildSpec) -> AnalyzeResponse:

    build_id = str(uuid.uuid4())[:8].upper()
    timestamp = datetime.now(timezone.utc)
    notes: List[str] = []

    # ── Step 1: Normalize input ────────────────────────────────────────────
    raw_dict = spec.model_dump()

    # ✅ FIXED LINE (THIS IS THE IMPORTANT CHANGE)
    normalized = normalize_build_spec(raw_dict, master_catalogue)

    cpu = normalized.get("cpu")
    gpu = normalized.get("gpu")
    motherboard = normalized.get("motherboard")
    ram = normalized.get("ram")
    storage = normalized.get("storage") or []
    psu = normalized.get("psu")
    case = normalized.get("case")
    cooler = normalized.get("cooler")
    monitor = normalized.get("monitor")
    usage_type = normalized.get("usage_type")
    budget_usd = normalized.get("budget_usd")
    preferred_brand = normalized.get("preferred_brand")
    region = normalized.get("region", "US")

    # ── Step 2: Recommendation engine — fill missing components ────────────
    recommendations = run_recommendations(
        cpu=cpu,
        gpu=gpu,
        motherboard=motherboard,
        ram=ram,
        storage=storage if storage else None,
        psu=psu,
        case=case,
        cooler=cooler,
        budget_usd=budget_usd,
        preferred_brand=preferred_brand,
        usage_type=usage_type,
    )
    inferred_tier = recommendations.inferred_tier

    auto_filled: List[str] = []
    for rec_part in recommendations.recommended_parts:
        cat = rec_part.category
        if cat == "CPU" and not cpu:
            cpu = rec_part.model
            auto_filled.append("CPU")
        elif cat == "GPU" and not gpu:
            gpu = rec_part.model
            auto_filled.append("GPU")
        elif cat == "Motherboard" and not motherboard:
            motherboard = rec_part.model
            auto_filled.append("Motherboard")
        elif cat == "RAM" and not ram:
            ram = {"size_gb": None, "type": None, "speed_mhz": None}
            auto_filled.append("RAM")
        elif cat == "Storage" and not storage:
            storage = [{"type": "NVMe", "capacity_gb": 1024}]
            auto_filled.append("Storage")
        elif cat == "PSU" and not psu:
            psu = rec_part.model
            auto_filled.append("PSU")
        elif cat == "Case" and not case:
            case = rec_part.model
            auto_filled.append("Case")
        elif cat == "Cooler" and not cooler:
            cooler = rec_part.model
            auto_filled.append("Cooler")

    if auto_filled:
        notes.append(
            f"Auto-filled {len(auto_filled)} missing component(s): {', '.join(auto_filled)}."
        )

    # ── Step 3: Compatibility ─────────────────────────────────────────────
    compatibility = run_compatibility_check(
        cpu=cpu,
        gpu=gpu,
        motherboard=motherboard,
        ram=ram if isinstance(ram, dict) else None,
        storage=storage if isinstance(storage, list) else [],
        psu=psu,
        case=case,
        cooler=cooler,
    )

    # ── Step 4: Build assembly ────────────────────────────────────────────
    completed_build: List[ResolvedComponent] = []

    for cat, model in [
        ("CPU", cpu),
        ("GPU", gpu),
        ("Motherboard", motherboard),
        ("PSU", psu),
        ("Case", case),
        ("Cooler", cooler),
        ("Monitor", monitor),
    ]:
        if model:
            comp = _resolve_component(cat, model)
            if comp:
                completed_build.append(comp)

    # ── Step 5: Pricing ───────────────────────────────────────────────────
    pricing: List[PricedPart] = []
    total = 0.0

    for comp in completed_build:
        priced = _price_or_predict(
            comp.model,
            comp.category,
            comp.brand,
            inferred_tier,
            usage_type,
        )
        pricing.append(priced)
        total += priced.price_usd

    currency = "USD"
    sym = fx_symbol(currency)

    return AnalyzeResponse(
        build_id=build_id,
        timestamp=timestamp,
        original_input=raw_dict,
        completed_build=completed_build,
        auto_filled_components=auto_filled,
        compatibility=compatibility,
        recommendations=recommendations,
        pricing=pricing,
        price_summary=PriceSummary(
            total_live_usd=round(total, 2),
            total_predicted_usd=0,
            total_combined_usd=round(total, 2),
            market_range=PriceRange(
                min_price=round(total * 0.9, 2),
                average_price=round(total, 2),
                max_price=round(total * 1.2, 2),
            ),
            live_parts_count=len(pricing),
            predicted_parts_count=0,
            currency=currency,
            region="US",
        ),
        notes=notes,
        inferred_tier=inferred_tier,
        usage_type=usage_type,
    )