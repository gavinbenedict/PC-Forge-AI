from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

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
from backend.utils.currency import symbol as fx_symbol
from backend.data.catalogue import master_catalogue

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _extract_brand(model_name: str) -> str:
    return model_name.split()[0] if model_name else "Unknown"


def _resolve_component(category: str, model_name: Optional[str]) -> Optional[ResolvedComponent]:
    if not model_name:
        return None

    return ResolvedComponent(
        category=category,
        brand=_extract_brand(model_name),
        model=model_name,
        specs={},
        is_auto_filled=False,
    )


def _price_or_predict(
    model_name: str,
    category: str,
    brand: str,
    tier: str,
    usage_type: Optional[str],
) -> PricedPart:
    """
    Always returns a valid PricedPart — never raises.
    Priority: pricing_service (DB/catalogue) → prediction_service → fallback.
    """
    # 1. Pricing service (DB + catalogue + fallback built-in)
    try:
        priced = pricing_service.get_price(model_name, category)
        if priced and priced.price_usd > 0:
            return priced
    except Exception as exc:
        logger.warning("pricing_service failed for %s: %s", model_name, exc)

    # 2. ML prediction
    try:
        predicted = prediction_service.build_priced_part_predicted(
            category=category,
            brand=brand,
            model_name=model_name,
            tier=tier,
            usage_type=usage_type,
            specs={},
        )
        if predicted and predicted.price_usd > 0:
            from backend.services.pricing_service import _CATEGORY_FALLBACK, _apply_gpu_floor
            floor = _CATEGORY_FALLBACK.get(category, 50.0)
            if category == "GPU":
                floor = _apply_gpu_floor(model_name, floor)
            if predicted.price_usd >= floor * 0.5:  # sanity: at least half the floor
                return predicted
            logger.warning("Prediction price %.2f below floor %.2f for %s — discarding",
                           predicted.price_usd, floor, model_name)
    except Exception as exc:
        logger.warning("prediction_service failed for %s: %s", model_name, exc)

    # 3. Hard fallback — guaranteed
    return pricing_service._fallback_priced_part(model_name, category)


# ─────────────────────────────────────────────
# MAIN ROUTE
# ─────────────────────────────────────────────

@router.post("/analyze-build", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_build(spec: BuildSpec) -> AnalyzeResponse:

    build_id = str(uuid.uuid4())[:8].upper()
    timestamp = datetime.now(timezone.utc)
    notes: List[str] = []

    raw_dict = spec.model_dump()

    if not raw_dict:
        raise HTTPException(status_code=400, detail="Empty build spec")

    # Normalize
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

    # Recommendations
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

    # Compatibility
    compatibility = run_compatibility_check(
        cpu=cpu,
        gpu=gpu,
        motherboard=motherboard,
        ram=ram if isinstance(ram, dict) else None,
        storage=storage,
        psu=psu,
        case=case,
        cooler=cooler,
    )

    # Build assembly
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
        comp = _resolve_component(cat, model)
        if comp:
            completed_build.append(comp)

    # Pricing
    pricing: List[PricedPart] = []
    total = 0.0

    # Price resolved single components (CPU, GPU, Motherboard, PSU, Case, Cooler, Monitor)
    for comp in completed_build:
        try:
            priced = _price_or_predict(
                comp.model,
                comp.category,
                comp.brand,
                inferred_tier,
                usage_type,
            )
            pricing.append(priced)
            total += priced.price_usd
        except Exception as e:
            logger.error("Pricing failed for %s: %s", comp.model, e)

    # Price RAM separately (it's a dict, not in completed_build)
    if ram and isinstance(ram, dict):
        ram_model = ram.get("model") or ram.get("name") or "Generic DDR5 32GB RAM"
        try:
            ram_priced = _price_or_predict(ram_model, "RAM", "Unknown", inferred_tier, usage_type)
            pricing.append(ram_priced)
            total += ram_priced.price_usd
        except Exception as e:
            logger.error("RAM pricing failed: %s", e)

    # Price storage drives (each entry in the list)
    for drive in storage:
        if not drive:
            continue
        drive_model = (
            drive.get("model") or drive.get("name") or "Generic 1TB NVMe SSD"
            if isinstance(drive, dict) else str(drive)
        )
        try:
            drive_priced = _price_or_predict(drive_model, "Storage", "Unknown", inferred_tier, usage_type)
            pricing.append(drive_priced)
            total += drive_priced.price_usd
        except Exception as e:
            logger.error("Storage pricing failed for %s: %s", drive_model, e)

    currency = "USD"

    return AnalyzeResponse(
        build_id=build_id,
        timestamp=timestamp,
        original_input=raw_dict,
        completed_build=completed_build,
        auto_filled_components=[],
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