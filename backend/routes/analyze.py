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

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Component resolution helpers ─────────────────────────────────────────────

def _extract_brand(model_name: str) -> str:
    """Extract brand prefix from model name."""
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
    """
    Try simulated price first, fall back to ML prediction.
    Priority: live/simulated > predicted.
    """
    priced = pricing_service.get_price(model_name, category)
    if priced:
        return priced
    # Fallback to ML prediction
    logger.debug("No simulated price for '%s' — using ML prediction.", model_name)
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
    """
    Full PC build analysis endpoint.
    
    Accepts a partial or complete PC specification and returns:
    - Completed build (with auto-filled missing components)
    - Compatibility report
    - Part-wise pricing (live/simulated + ML prediction fallback)
    - Recommendation engine output
    - Total price + market price range
    - CSV/Excel export (via separate endpoints)
    """
    build_id = str(uuid.uuid4())[:8].upper()
    timestamp = datetime.now(timezone.utc)
    notes: List[str] = []

    # ── Step 1: Normalize input ────────────────────────────────────────────
    raw_dict = spec.model_dump()
    normalized = normalize_build_spec(raw_dict)

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

    # Merge auto-filled parts into the build
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
            f"Auto-filled {len(auto_filled)} missing component(s): {', '.join(auto_filled)}. "
            "Selections are based on compatibility rules and build tier inference."
        )

    # ── Step 3: Compatibility check ────────────────────────────────────────
    ram_dict = ram if isinstance(ram, dict) else None
    storage_list = storage if isinstance(storage, list) else []
    
    compatibility = run_compatibility_check(
        cpu=cpu,
        gpu=gpu,
        motherboard=motherboard,
        ram=ram_dict,
        storage=storage_list,
        psu=psu,
        case=case,
        cooler=cooler,
    )

    if compatibility.status == "invalid":
        notes.append(
            f"⚠️ Compatibility issues detected ({len([i for i in compatibility.issues if i.severity == 'error'])} errors). "
            "Review the compatibility report for suggested fixes."
        )
    elif compatibility.status == "warning":
        notes.append("ℹ️ Minor compatibility warnings detected. Build should function, but review recommendations.")

    # ── Step 4: Assemble completed build ───────────────────────────────────
    completed_build: List[ResolvedComponent] = []

    component_map = [
        ("CPU",         cpu,         None),
        ("GPU",         gpu,         None),
        ("Motherboard", motherboard, None),
        ("PSU",         psu,         None),
        ("Case",        case,        None),
        ("Cooler",      cooler,      None),
        ("Monitor",     monitor,     None),
    ]

    for cat, model, brand in component_map:
        if model:
            comp = _resolve_component(
                category=cat,
                model_name=model,
                brand=brand,
                is_auto_filled=cat in auto_filled,
            )
            if comp:
                completed_build.append(comp)

    # RAM component
    if ram:
        if isinstance(ram, dict):
            ram_model = f"{ram.get('brand', 'Generic')} {ram.get('type','DDR5')}-{ram.get('speed_mhz',6000)} {ram.get('size_gb',32)}GB"
        else:
            ram_model = str(ram)
        # Use recommendation model name if available
        for rp in recommendations.recommended_parts:
            if rp.category == "RAM":
                ram_model = rp.model
                break
        comp = _resolve_component("RAM", ram_model, is_auto_filled="RAM" in auto_filled)
        if comp:
            completed_build.append(comp)

    # Storage components
    if storage_list:
        for stor_item in storage_list:
            if isinstance(stor_item, dict):
                cap = stor_item.get("capacity_gb", 1024)
                stor_type = stor_item.get("type", "NVMe")
                stor_model = f"Generic {stor_type} {cap//1024}TB"
            else:
                stor_model = str(stor_item)
            # Use recommendation model name if available
            for rp in recommendations.recommended_parts:
                if rp.category == "Storage":
                    stor_model = rp.model
                    break
            comp = _resolve_component("Storage", stor_model, is_auto_filled="Storage" in auto_filled)
            if comp:
                completed_build.append(comp)
                break  # Only primary storage for display

    # ── Step 5: Price all components ───────────────────────────────────────
    pricing: List[PricedPart] = []
    live_total = 0.0
    predicted_total = 0.0
    live_count = 0
    pred_count = 0
    all_prices = []

    # Map component to pricing call
    pricing_targets = [
        (c.category, c.model) for c in completed_build
    ]

    # Also include recommendation models if they replaced None
    for rp in recommendations.recommended_parts:
        if rp.category not in [c.category for c in completed_build]:
            pricing_targets.append((rp.category, rp.model))
        elif rp.is_auto_filled:
            # Replace generic name with rec model
            pass

    for category, model in pricing_targets:
        if not model:
            continue
        brand = _extract_brand(model)
        priced = _price_or_predict(
            model_name=model,
            category=category,
            brand=brand,
            tier=inferred_tier,
            usage_type=usage_type,
        )
        pricing.append(priced)
        all_prices.append(priced.price_usd)

        if priced.source in ("live", "simulated"):
            live_total += priced.price_usd
            live_count += 1
        else:
            predicted_total += priced.price_usd
            pred_count += 1

    if pred_count > 0:
        notes.append(
            f"📊 {pred_count} component price(s) estimated via ML prediction (marked as 'PREDICTED'). "
            "These are approximate values based on market trends."
        )

    # ── Step 6: Currency conversion ────────────────────────────────────────
    combined_total = live_total + predicted_total  # base USD total
    _REGION_CURRENCY = {
        "US": "USD", "EU": "EUR", "UK": "GBP",
        "CA": "CAD", "AU": "AUD", "IN": "INR",
    }
    currency = _REGION_CURRENCY.get(region.upper(), "USD")

    if currency != "USD":
        converted_pricing: List[PricedPart] = []
        for p in pricing:
            converted_pricing.append(PricedPart(
                **{**p.model_dump(),
                   "price_usd": fx_convert(p.price_usd, currency),
                   "currency": currency}
            ))
        pricing = converted_pricing
        live_total      = fx_convert(live_total, currency)
        predicted_total = fx_convert(predicted_total, currency)
        combined_total  = fx_convert(combined_total, currency)

    # ── Step 7: Market price range ─────────────────────────────────────────
    if all_prices:
        import statistics
        market_range = PriceRange(
            min_price=round(combined_total * 0.88, 2),
            average_price=round(combined_total, 2),
            max_price=round(combined_total * 1.18, 2),
        )
    else:
        market_range = PriceRange(min_price=0.0, average_price=0.0, max_price=0.0)

    price_summary = PriceSummary(
        total_live_usd=round(live_total, 2),
        total_predicted_usd=round(predicted_total, 2),
        total_combined_usd=round(combined_total, 2),
        market_range=market_range,
        live_parts_count=live_count,
        predicted_parts_count=pred_count,
        currency=currency,
        region=region,
    )

    sym = fx_symbol(currency)
    notes.append(
        f"💵 Total: {sym}{combined_total:.2f} {currency} "
        f"(Simulated: {sym}{live_total:.2f} | Predicted: {sym}{predicted_total:.2f}). "
        f"Market range: {sym}{market_range.min_price:.2f} – {sym}{market_range.max_price:.2f}."
    )

    return AnalyzeResponse(
        build_id=build_id,
        timestamp=timestamp,
        original_input=raw_dict,
        completed_build=completed_build,
        auto_filled_components=auto_filled,
        compatibility=compatibility,
        recommendations=recommendations,
        pricing=pricing,
        price_summary=price_summary,
        notes=notes,
        inferred_tier=inferred_tier,
        usage_type=usage_type,
    )
