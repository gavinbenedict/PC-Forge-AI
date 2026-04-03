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
from backend.data.catalogue import master_catalogue

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Required categories that must always be present ─────────────────────────
REQUIRED_CATEGORIES = ["CPU", "GPU", "Motherboard", "RAM", "Storage", "PSU", "Case", "Cooler"]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_brand(model_name: str) -> str:
    if not model_name:
        return "Unknown"
    return model_name.split()[0]


def _resolve_component(
    category: str,
    model_name: Optional[str],
    is_auto_filled: bool = False,
) -> Optional[ResolvedComponent]:
    if not model_name or not str(model_name).strip():
        return None
    return ResolvedComponent(
        category=category,
        brand=_extract_brand(str(model_name).strip()),
        model=str(model_name).strip(),
        specs={},
        is_auto_filled=is_auto_filled,
    )


def _ram_to_model_name(ram: Any) -> Optional[str]:
    """
    Convert a RAMSpec Pydantic object, dict, or string to a readable model name.
    Never raises. Returns None if nothing can be extracted.
    """
    if ram is None:
        return None
    if isinstance(ram, str):
        return ram.strip() or None
    # Pydantic model → dict
    if hasattr(ram, "model_dump"):
        try:
            ram = ram.model_dump()
        except Exception:
            return "Generic DDR5 32GB RAM"
    if not isinstance(ram, dict):
        return "Generic DDR5 32GB RAM"

    # Try explicit model/name first
    model = ram.get("model") or ram.get("name")
    if model:
        return str(model).strip()

    size = ram.get("size_gb") or ram.get("capacity_gb")
    rtype = ram.get("type") or "DDR5"
    speed = ram.get("speed_mhz")

    if size and speed:
        return f"Generic {rtype}-{speed} {size}GB RAM"
    if size:
        return f"Generic {rtype} {size}GB RAM"
    # At minimum, return a plausible placeholder so pricing still works
    return f"Generic DDR5 32GB RAM"


def _storage_to_model_name(drive: Any) -> Optional[str]:
    """
    Convert a StorageSpec Pydantic object, dict, or string to a model name.
    """
    if drive is None:
        return None
    if isinstance(drive, str):
        return drive.strip() or None
    if hasattr(drive, "model_dump"):
        try:
            drive = drive.model_dump()
        except Exception:
            return "Generic 1TB NVMe SSD"
    if not isinstance(drive, dict):
        return "Generic 1TB NVMe SSD"

    model = drive.get("model") or drive.get("name")
    if model:
        return str(model).strip()

    dtype = drive.get("type") or drive.get("interface") or "NVMe"
    capacity = drive.get("capacity_gb")
    if capacity:
        tb = int(capacity) // 1024
        gb = int(capacity) % 1024
        size_str = f"{tb}TB" if tb and not gb else f"{capacity}GB"
        return f"Generic {size_str} {dtype} SSD"
    return "Generic 1TB NVMe SSD"


def _price_or_predict(
    model_name: str,
    category: str,
    brand: str,
    tier: str,
    usage_type: Optional[str],
) -> PricedPart:
    """
    Always returns a valid PricedPart with price_usd > 0.
    Three-stage fallback — never raises.
    """
    # Stage 1: pricing_service (DB + catalogue + GPU floor built in)
    try:
        priced = pricing_service.get_price(model_name, category)
        if priced and priced.price_usd > 0:
            return priced
    except Exception as exc:
        logger.warning("pricing_service failed for '%s' (%s): %s", model_name, category, exc)

    # Stage 2: ML prediction with sanity floor
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
            if predicted.price_usd >= floor * 0.5:
                return predicted
    except Exception as exc:
        logger.warning("prediction_service failed for '%s' (%s): %s", model_name, category, exc)

    # Stage 3: Hard category fallback — always succeeds
    return pricing_service._fallback_priced_part(model_name, category)


# ─── Main Route ───────────────────────────────────────────────────────────────

@router.post("/analyze-build", response_model=AnalyzeResponse, tags=["Analysis"])
async def analyze_build(spec: BuildSpec) -> AnalyzeResponse:

    build_id  = str(uuid.uuid4())[:8].upper()
    timestamp = datetime.now(timezone.utc)
    notes: List[str] = []

    raw_dict = spec.model_dump()
    if not raw_dict:
        raise HTTPException(status_code=400, detail="Empty build spec")

    # ── Step 1: Normalize text input ──────────────────────────────────────────
    normalized = normalize_build_spec(raw_dict, master_catalogue)

    cpu         = normalized.get("cpu")
    gpu         = normalized.get("gpu")
    motherboard = normalized.get("motherboard")
    psu         = normalized.get("psu")
    case        = normalized.get("case")
    cooler      = normalized.get("cooler")
    monitor     = normalized.get("monitor")
    usage_type  = normalized.get("usage_type")
    budget_usd  = normalized.get("budget_usd")
    preferred_brand = normalized.get("preferred_brand")

    # RAM — may be a RAMSpec Pydantic object, dict, or None
    ram_raw  = normalized.get("ram") or spec.ram
    ram_name = _ram_to_model_name(ram_raw)

    # Storage — may be List[StorageSpec], list of dicts, or None
    storage_raw: List[Any] = []
    raw_storage = normalized.get("storage") or spec.storage
    if raw_storage:
        storage_raw = list(raw_storage) if isinstance(raw_storage, (list, tuple)) else [raw_storage]

    # ── Step 2: Get auto-fill recommendations ─────────────────────────────────
    # Pass structured RAM/storage objects so recommendation service can check
    # whether they are present (non-None) and skip auto-fill for those slots.
    rec_ram = ram_raw if (
        isinstance(ram_raw, dict) or hasattr(ram_raw, "model_dump")
    ) else None
    rec_storage = storage_raw if storage_raw else None

    recommendations = run_recommendations(
        cpu=cpu,
        gpu=gpu,
        motherboard=motherboard,
        ram=rec_ram,
        storage=rec_storage,
        psu=psu,
        case=case,
        cooler=cooler,
        budget_usd=budget_usd,
        preferred_brand=preferred_brand,
        usage_type=usage_type,
    )
    inferred_tier = recommendations.inferred_tier

    # ── Step 3: Merge user components + auto-filled components ────────────────
    # user_components: what the user explicitly provided
    user_components: Dict[str, str] = {}
    if cpu:         user_components["CPU"]         = cpu
    if gpu:         user_components["GPU"]         = gpu
    if motherboard: user_components["Motherboard"] = motherboard
    if psu:         user_components["PSU"]         = psu
    if case:        user_components["Case"]        = case
    if cooler:      user_components["Cooler"]      = cooler

    # auto_filled: from recommendation engine, only for missing slots
    auto_filled: Dict[str, str] = {}
    for rec in recommendations.recommended_parts:
        cat = rec.category
        if cat not in user_components and cat not in ("RAM", "Storage"):
            auto_filled[cat] = rec.model

    # RAM auto-fill
    ram_auto: Optional[str] = None
    if not ram_name:
        ram_rec = next(
            (r for r in recommendations.recommended_parts if r.category == "RAM"),
            None,
        )
        if ram_rec:
            ram_auto = ram_rec.model
            auto_filled["RAM"] = ram_rec.model

    # Storage auto-fill
    storage_auto: List[str] = []
    if not storage_raw:
        stor_rec = next(
            (r for r in recommendations.recommended_parts if r.category == "Storage"),
            None,
        )
        if stor_rec:
            storage_auto = [stor_rec.model]
            auto_filled["Storage"] = stor_rec.model

    # ── Step 4: Resolve final model name strings ───────────────────────────────
    final: Dict[str, Optional[str]] = {
        "CPU":         user_components.get("CPU")         or auto_filled.get("CPU"),
        "GPU":         user_components.get("GPU")         or auto_filled.get("GPU"),
        "Motherboard": user_components.get("Motherboard") or auto_filled.get("Motherboard"),
        "PSU":         user_components.get("PSU")         or auto_filled.get("PSU"),
        "Case":        user_components.get("Case")        or auto_filled.get("Case"),
        "Cooler":      user_components.get("Cooler")      or auto_filled.get("Cooler"),
        "RAM":         ram_name or ram_auto,
        "Monitor":     monitor,
    }
    final_storage: List[str] = (
        [n for n in (_storage_to_model_name(d) for d in storage_raw) if n]
        or storage_auto
    )

    # ── Step 5: Compatibility check ────────────────────────────────────────────
    compatibility = run_compatibility_check(
        cpu=final["CPU"],
        gpu=final["GPU"],
        motherboard=final["Motherboard"],
        ram=rec_ram,
        storage=storage_raw,
        psu=final["PSU"],
        case=final["Case"],
        cooler=final["Cooler"],
    )

    # ── Step 6: Assemble completed_build ─────────────────────────────────────
    completed_build: List[ResolvedComponent] = []
    auto_filled_names: List[str] = list(auto_filled.keys())

    # Scalar components
    for cat in ["CPU", "GPU", "Motherboard", "PSU", "Case", "Cooler", "Monitor"]:
        model_str = final.get(cat)
        comp = _resolve_component(cat, model_str, is_auto_filled=(cat in auto_filled))
        if comp:
            completed_build.append(comp)

    # RAM
    if final["RAM"]:
        completed_build.append(
            _resolve_component("RAM", final["RAM"], is_auto_filled=("RAM" in auto_filled))
        )

    # Storage drive(s)
    for drive_name in final_storage:
        if drive_name:
            completed_build.append(
                _resolve_component("Storage", drive_name, is_auto_filled=("Storage" in auto_filled))
            )

    # ── Step 7: Price every component ────────────────────────────────────────
    pricing: List[PricedPart] = []
    predicted_count = 0
    total = 0.0

    for comp in completed_build:
        try:
            priced = _price_or_predict(
                comp.model,
                comp.category,
                comp.brand,
                inferred_tier,
                usage_type,
            )
            if priced.source == "predicted":
                predicted_count += 1
            pricing.append(priced)
            total += priced.price_usd
        except Exception as e:
            logger.error("Pricing loop failed for '%s' (%s): %s", comp.model, comp.category, e)

    # ── Step 8: Sanity net — ensure EVERY required category has a price ───────
    priced_cats = {p.category for p in pricing}
    for missing_cat in REQUIRED_CATEGORIES:
        if missing_cat not in priced_cats:
            placeholder = f"Generic {missing_cat}"
            logger.warning("Injecting fallback for missing category: %s", missing_cat)
            fallback = pricing_service._fallback_priced_part(placeholder, missing_cat)
            pricing.append(fallback)
            total += fallback.price_usd
            # Also add to completed_build if absent
            if not any(c.category == missing_cat for c in completed_build):
                comp = _resolve_component(missing_cat, placeholder, is_auto_filled=True)
                if comp:
                    completed_build.append(comp)
                    if missing_cat not in auto_filled_names:
                        auto_filled_names.append(missing_cat)

    live_count = len(pricing) - predicted_count

    # ── Step 9: Return response ───────────────────────────────────────────────
    return AnalyzeResponse(
        build_id=build_id,
        timestamp=timestamp,
        original_input=raw_dict,
        completed_build=completed_build,
        auto_filled_components=auto_filled_names,
        compatibility=compatibility,
        recommendations=recommendations,
        pricing=pricing,
        price_summary=PriceSummary(
            total_live_usd=round(total, 2),
            total_predicted_usd=round(
                sum(p.price_usd for p in pricing if p.source == "predicted"), 2
            ),
            total_combined_usd=round(total, 2),
            market_range=PriceRange(
                min_price=round(total * 0.90, 2),
                average_price=round(total, 2),
                max_price=round(total * 1.20, 2),
            ),
            live_parts_count=live_count,
            predicted_parts_count=predicted_count,
            currency="USD",
            region="US",
        ),
        notes=notes,
        inferred_tier=inferred_tier,
        usage_type=usage_type,
    )