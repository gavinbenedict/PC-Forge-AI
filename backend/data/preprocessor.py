"""
PCForge AI — Master Catalogue Preprocessor
===========================================
Ingestion pipeline that transforms raw dataset files into a clean,
normalised, validated master catalogue.

Pipeline stages (in order):
  1. load_raw       — JSON or CSV
  2. resolve_types  — map raw type field → canonical category
  3. filter_year    — drop entries older than MIN_RELEASE_YEAR
  4. normalise      — standardise fields, resolve aliases, clean strings
  5. filter_complete — drop entries missing required fields
  6. deduplicate    — remove exact/near-duplicate entries
  7. assign_ids     — generate deterministic hash-based IDs
  8. expand_variants — GPU VRAM/AIB variants, RAM/Storage capacity variants

Usage:
    from backend.data.preprocessor import Preprocessor
    pipeline = Preprocessor()
    components = pipeline.run(Path("data/raw/pc_parts.json"))
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from backend.data.raw_schema import (
    CATEGORY_ALIASES,
    EFFICIENCY_ALIASES,
    FIELD_ALIASES,
    FORM_FACTOR_ALIASES,
    INTERFACE_ALIASES,
    MIN_RELEASE_YEAR,
    RAM_TYPE_ALIASES,
    REQUIRED_FIELDS,
    SOCKET_ALIASES,
    YEAR_EXEMPT_CATEGORIES,
    resolve_category,
    resolve_field,
)

logger = logging.getLogger("pcforge.preprocessor")

# ─── GPU Variant Templates ─────────────────────────────────────────────────────
# Each AIB variant = (suffix, price_multiplier, length_adj_mm)
_GPU_AIB_VARIANTS: List[Tuple[str, str, float, int]] = [
    # (brand_prefix, suffix, price_mult, len_adj)
    ("ASUS",    "TUF Gaming OC",          1.06,  +5),
    ("ASUS",    "ROG STRIX OC",           1.12,  +15),
    ("MSI",     "Gaming X Trio",          1.08,  +10),
    ("MSI",     "Ventus 3X OC",           1.04,  +5),
    ("Gigabyte","AORUS Master",           1.11,  +15),
    ("Gigabyte","Gaming OC",              1.05,  +5),
    ("EVGA",    "FTW3 Ultra Gaming",      1.09,  +12),
    ("Zotac",   "AMP Extreme",            1.07,  +10),
    ("Sapphire","NITRO+ OC",             1.08,  +10),   # AMD
    ("Sapphire","PULSE",                  1.03,  +2),    # AMD
    ("PowerColor","Red Devil OC",         1.09,  +12),   # AMD
    ("XFX",     "SPEEDSTER MERC 319",     1.06,  +8),    # AMD
]

# VRAM variants to generate when a GPU is found without explicit variant info.
# Format: (vram_gb, price_multiplier) relative to base
_GPU_VRAM_TIERS: Dict[str, List[Tuple[int, float]]] = {
    # NVIDIA RTX 40-series
    "RTX 4090":      [(24, 1.0)],
    "RTX 4080 Super":[(16, 1.0)],
    "RTX 4080":      [(16, 1.0)],
    "RTX 4070 Ti Super": [(16, 1.0)],
    "RTX 4070 Ti":   [(12, 1.0)],
    "RTX 4070 Super":[(12, 1.0)],
    "RTX 4070":      [(12, 1.0)],
    "RTX 4060 Ti":   [(8, 1.0), (16, 1.15)],
    "RTX 4060":      [(8, 1.0)],
    # NVIDIA RTX 30-series
    "RTX 3090 Ti":   [(24, 1.0)],
    "RTX 3090":      [(24, 1.0)],
    "RTX 3080 Ti":   [(12, 1.0)],
    "RTX 3080":      [(10, 1.0), (12, 1.12)],
    "RTX 3070 Ti":   [(8, 1.0)],
    "RTX 3070":      [(8, 1.0)],
    "RTX 3060 Ti":   [(8, 1.0)],
    "RTX 3060":      [(12, 1.0)],
    "RTX 3050":      [(8, 1.0)],
    # NVIDIA GTX 16-series
    "GTX 1660 Super":[(6, 1.0)],
    "GTX 1660 Ti":   [(6, 1.0)],
    "GTX 1660":      [(6, 1.0)],
    "GTX 1650 Super":[(4, 1.0)],
    "GTX 1650":      [(4, 1.0)],
    # NVIDIA GTX 10-series
    "GTX 1080 Ti":   [(11, 1.0)],
    "GTX 1080":      [(8, 1.0)],
    "GTX 1070 Ti":   [(8, 1.0)],
    "GTX 1070":      [(8, 1.0)],
    "GTX 1060":      [(3, 1.0), (6, 1.20)],
    "GTX 1050 Ti":   [(4, 1.0)],
    "GTX 1050":      [(2, 1.0)],
    # AMD RX 7000-series
    "RX 7900 XTX":   [(24, 1.0)],
    "RX 7900 XT":    [(20, 1.0)],
    "RX 7900 GRE":   [(16, 1.0)],
    "RX 7800 XT":    [(16, 1.0)],
    "RX 7700 XT":    [(12, 1.0)],
    "RX 7600 XT":    [(16, 1.0)],
    "RX 7600":       [(8, 1.0)],
    # AMD RX 6000-series
    "RX 6950 XT":    [(16, 1.0)],
    "RX 6900 XT":    [(16, 1.0)],
    "RX 6800 XT":    [(16, 1.0)],
    "RX 6800":       [(16, 1.0)],
    "RX 6700 XT":    [(12, 1.0)],
    "RX 6700":       [(10, 1.0)],
    "RX 6650 XT":    [(8, 1.0)],
    "RX 6600 XT":    [(8, 1.0)],
    "RX 6600":       [(8, 1.0)],
    "RX 6500 XT":    [(4, 1.0)],
    # AMD RX 500-series
    "RX 590":        [(8, 1.0)],
    "RX 580":        [(4, 1.0), (8, 1.15)],
    "RX 570":        [(4, 1.0), (8, 1.18)],
    "RX 560":        [(4, 1.0)],
}

# RAM capacity tiers to generate per base entry (mult on price)
_RAM_CAPACITY_VARIANTS: List[Tuple[int, float]] = [
    (8,  0.45),
    (16, 0.75),
    (32, 1.0),
    (64, 1.75),
    (128, 3.2),
]

# Storage capacity tiers
_STORAGE_CAPACITY_VARIANTS: List[Tuple[int, float]] = [
    (256,  0.35),
    (512,  0.55),
    (1024, 1.0),
    (2048, 1.75),
    (4096, 3.2),
]


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _clean_str(val: Any) -> str:
    """Strip and title-case a string value."""
    return str(val).strip() if val is not None else ""


def _clean_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(re.sub(r"[^0-9.]", "", str(val)))
    except (ValueError, TypeError):
        return None


def _clean_int(val: Any) -> Optional[int]:
    f = _clean_float(val)
    return int(f) if f is not None else None


def _make_id(category: str, brand: str, model: str, extra: str = "") -> str:
    """Generate a deterministic 12-char hex ID from key fields."""
    key = f"{category}::{brand.lower()}::{model.lower()}::{extra.lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def _build_full_name(brand: str, model: str) -> str:
    """Create canonical full name, avoiding double-brand like 'ASUS ASUS TUF...'."""
    brand_lower = brand.strip().lower()
    model_lower = model.strip().lower()
    # If model already starts with brand, don't prepend again
    return model.strip() if model_lower.startswith(brand_lower) else f"{brand.strip()} {model.strip()}"


def _normalise_form_factor(raw: str) -> str:
    return FORM_FACTOR_ALIASES.get(str(raw).strip().lower(), str(raw).strip())


def _normalise_socket(raw: str) -> str:
    return SOCKET_ALIASES.get(str(raw).strip().lower(), str(raw).strip().upper())


def _normalise_ram_type(raw: str) -> str:
    return RAM_TYPE_ALIASES.get(str(raw).strip().lower(), str(raw).strip().upper())


def _normalise_interface(raw: str) -> str:
    return INTERFACE_ALIASES.get(str(raw).strip().lower(), str(raw).strip())


def _normalise_efficiency(raw: str) -> str:
    return EFFICIENCY_ALIASES.get(str(raw).strip().lower(), str(raw).strip())


# ─── Stage Functions ──────────────────────────────────────────────────────────

def _load_raw_json(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Try common wrapper keys
        for key in ("components", "parts", "items", "data", "products"):
            if key in data and isinstance(data[key], list):
                return data[key]
    raise ValueError(f"Unrecognised JSON structure in {path}. "
                     "Expected a list or dict with 'components'/'parts'/'items' key.")


def _load_raw_csv(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def _load_raw(path: Path) -> List[Dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in (".json", ".jsonl"):
        return _load_raw_json(path)
    elif suffix in (".csv", ".tsv"):
        return _load_raw_csv(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .json or .csv")


def _resolve_type(raw: Dict[str, Any]) -> Optional[str]:
    """Extract and resolve the component category from a raw entry."""
    for key in ("type", "category", "component_type", "part_type", "class"):
        if key in raw and raw[key]:
            cat = resolve_category(str(raw[key]).strip().lower())
            if cat:
                return cat
    return None


def _passes_year_filter(raw: Dict[str, Any], category: str) -> bool:
    if category in YEAR_EXEMPT_CATEGORIES:
        return True
    year = _clean_int(resolve_field(raw, "year"))
    if year is None:
        return True  # No year info — keep (be permissive)
    return year >= MIN_RELEASE_YEAR


def _normalise_entry(raw: Dict[str, Any], category: str) -> Dict[str, Any]:
    """Normalise a raw entry into a clean canonical dict."""
    r = resolve_field  # shorthand

    brand  = _clean_str(r(raw, "brand"))
    model  = _clean_str(r(raw, "model"))
    price  = _clean_float(r(raw, "price_usd")) or 0.0
    year   = _clean_int(r(raw, "year"))

    # Build canonical name
    full_name = _build_full_name(brand, model)

    out: Dict[str, Any] = {
        "_category": category,
        "brand":     brand,
        "model":     model,
        "full_name": full_name,
        "price_usd": price,
        "year":      year,
    }

    if category == "CPU":
        socket         = _clean_str(r(raw, "socket"))
        cores          = _clean_int(r(raw, "cores"))
        threads        = _clean_int(r(raw, "threads"))
        base_clock     = _clean_float(r(raw, "base_clock_ghz"))
        boost_clock    = _clean_float(r(raw, "boost_clock_ghz"))
        tdp            = _clean_int(r(raw, "tdp_w"))
        generation     = _clean_int(r(raw, "generation"))
        out.update({
            "socket":          _normalise_socket(socket) if socket else None,
            "cores":           cores,
            "threads":         threads or (cores * 2 if cores else None),
            "base_clock_ghz":  base_clock,
            "boost_clock_ghz": boost_clock,
            "tdp_w":           tdp,
            "generation":      generation,
        })

    elif category == "GPU":
        vram       = _clean_int(r(raw, "vram_gb"))
        mem_type   = _clean_str(r(raw, "memory_type")) or "GDDR6"
        power_draw = _clean_int(r(raw, "power_draw_w"))
        length     = _clean_int(r(raw, "length_mm"))
        out.update({
            "vram_gb":      vram,
            "memory_type":  mem_type,
            "power_draw_w": power_draw,
            "length_mm":    length or 270,   # default reasonable length
            "variant":      _clean_str(r(raw, "variant")) or "Reference",
        })

    elif category == "Motherboard":
        socket    = _clean_str(r(raw, "socket"))
        chipset   = _clean_str(r(raw, "chipset"))
        ff        = _clean_str(r(raw, "form_factor"))
        ram_type  = r(raw, "ram_type")
        max_ram   = _clean_int(r(raw, "max_ram_gb"))

        # ram_type may be list or string
        if isinstance(ram_type, list):
            ram_types = [_normalise_ram_type(t) for t in ram_type]
        elif isinstance(ram_type, str):
            # Could be "DDR4/DDR5" or "DDR4, DDR5"
            parts = re.split(r"[/,|]", ram_type)
            ram_types = [_normalise_ram_type(p.strip()) for p in parts if p.strip()]
        else:
            ram_types = []

        out.update({
            "socket":      _normalise_socket(socket) if socket else None,
            "chipset":     chipset.upper() if chipset else None,
            "form_factor": _normalise_form_factor(ff) if ff else "ATX",
            "ram_types":   ram_types,
            "max_ram_gb":  max_ram or 128,
        })

    elif category == "RAM":
        ram_type   = _clean_str(r(raw, "ram_type"))
        capacity   = _clean_int(r(raw, "capacity_gb"))
        speed      = _clean_int(r(raw, "speed_mhz"))
        modules    = _clean_int(r(raw, "modules")) or 2
        out.update({
            "ram_type":   _normalise_ram_type(ram_type) if ram_type else None,
            "capacity_gb": capacity,
            "speed_mhz":  speed,
            "modules":    modules,
        })

    elif category == "Storage":
        interface  = _clean_str(r(raw, "interface"))
        capacity   = _clean_int(r(raw, "capacity_gb"))
        out.update({
            "interface":   _normalise_interface(interface) if interface else "NVMe Gen3",
            "capacity_gb": capacity,
        })

    elif category == "PSU":
        wattage    = _clean_int(r(raw, "wattage_w"))
        efficiency = _clean_str(r(raw, "efficiency"))
        modular    = r(raw, "modular")
        out.update({
            "wattage_w":  wattage,
            "efficiency": _normalise_efficiency(efficiency) if efficiency else "80+ Gold",
            "modular":    bool(modular) if modular is not None else True,
        })

    elif category == "Case":
        ffs        = r(raw, "supported_form_factors")
        gpu_cl     = _clean_int(r(raw, "gpu_clearance_mm"))
        cooler_cl  = _clean_int(r(raw, "cooler_clearance_mm"))
        if isinstance(ffs, list):
            form_factors = [_normalise_form_factor(f) for f in ffs]
        elif isinstance(ffs, str):
            parts = re.split(r"[/,|]", ffs)
            form_factors = [_normalise_form_factor(p.strip()) for p in parts if p.strip()]
        else:
            form_factors = ["ATX", "mATX"]
        out.update({
            "supported_form_factors": form_factors,
            "gpu_clearance_mm":       gpu_cl or 350,
            "cooler_clearance_mm":    cooler_cl or 160,
        })

    elif category == "Cooler":
        cooler_type = _clean_str(r(raw, "cooler_type"))
        tdp_rating  = _clean_int(r(raw, "tdp_rating_w"))
        height      = _clean_int(r(raw, "height_mm"))
        radiator    = _clean_int(r(raw, "radiator_mm"))
        # Detect AIO vs air
        is_aio      = "aio" in cooler_type.lower() or "liquid" in cooler_type.lower() or bool(radiator)
        out.update({
            "cooler_type":  "AIO" if is_aio else "Air",
            "tdp_rating_w": tdp_rating or 150,
            "height_mm":    height if not is_aio else radiator or 27,
            "is_aio":       is_aio,
        })

    return out


def _passes_completeness(entry: Dict[str, Any], category: str) -> bool:
    """Check that all required canonical fields are non-None."""
    required = REQUIRED_FIELDS.get(category, [])
    for field in required:
        val = entry.get(field)
        if val is None or val == "" or (isinstance(val, list) and len(val) == 0):
            return False
    return True


def _dedup_key(entry: Dict[str, Any]) -> str:
    """Create a deduplication key from uniquely identifying fields."""
    cat   = entry.get("_category", "")
    brand = entry.get("brand", "").lower().strip()
    model = entry.get("model", "").lower().strip()
    # Category-specific key extension
    ext = ""
    if cat == "GPU":
        ext = str(entry.get("vram_gb", ""))
    elif cat == "RAM":
        ext = f"{entry.get('capacity_gb', '')}_{entry.get('ram_type', '')}"
    elif cat == "Storage":
        ext = f"{entry.get('capacity_gb', '')}_{entry.get('interface', '')}"
    return f"{cat}::{brand}::{model}::{ext}"


def _assign_id(entry: Dict[str, Any]) -> Dict[str, Any]:
    cat   = entry.get("_category", "unknown")
    brand = entry.get("brand", "")
    model = entry.get("model", "")
    ext   = entry.get("variant", "") or str(entry.get("vram_gb", ""))
    entry["id"] = _make_id(cat, brand, model, ext)
    return entry


# ─── Variant Expansion ─────────────────────────────────────────────────────────

def _expand_gpu_variants(base: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Expand a base GPU entry into multiple AIB variants + VRAM tiers.
    Returns the base entry (potentially updated) + new variant entries.
    """
    results: List[Dict[str, Any]] = []
    model_str  = base.get("model", "")
    brand_str  = base.get("brand", "NVIDIA")
    base_price = base.get("price_usd", 0.0)
    base_len   = base.get("length_mm", 270)

    # Find matching VRAM tiers
    matched_key = None
    for key in _GPU_VRAM_TIERS:
        if key.lower() in model_str.lower():
            matched_key = key
            break

    vram_entries: List[Tuple[int, float]] = []
    if matched_key:
        vram_entries = _GPU_VRAM_TIERS[matched_key]
    elif base.get("vram_gb"):
        vram_entries = [(base["vram_gb"], 1.0)]
    else:
        vram_entries = [(8, 1.0)]

    # Determine which AIB variants to use (NVIDIA vs AMD)
    is_amd = "amd" in brand_str.lower() or any(
        x in model_str.lower() for x in ["rx ", "radeon"]
    )
    aib_pool = [v for v in _GPU_AIB_VARIANTS if
                (is_amd and v[0] in ("Sapphire", "PowerColor", "XFX", "MSI", "ASUS", "Gigabyte", "Zotac")) or
                (not is_amd and v[0] in ("ASUS", "MSI", "Gigabyte", "EVGA", "Zotac"))]

    for vram_gb, vram_price_mult in vram_entries:
        vram_price = round(base_price * vram_price_mult, 2)

        for aib_brand, aib_suffix, price_mult, len_adj in aib_pool[:4]:  # max 4 AIB variants
            variant = base.copy()
            variant_model = f"{model_str} {vram_gb}GB"
            full_variant_name = f"{aib_brand} {model_str} {aib_suffix} {vram_gb}GB"

            variant.update({
                "brand":      aib_brand,
                "model":      f"{model_str} {aib_suffix} {vram_gb}GB",
                "full_name":  full_variant_name,
                "vram_gb":    vram_gb,
                "price_usd":  round(vram_price * price_mult, 2),
                "length_mm":  base_len + len_adj,
                "variant":    aib_suffix,
                "parent_model": model_str,
                "id":         _make_id("GPU", aib_brand, variant_model, aib_suffix),
            })
            results.append(variant)

    return results


def _expand_ram_variants(base: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate capacity variants (8/16/32/64/128GB) from a base RAM entry."""
    results: List[Dict[str, Any]] = []
    base_price    = base.get("price_usd", 40.0)
    base_capacity = base.get("capacity_gb", 16)
    ram_type      = base.get("ram_type", "DDR4")
    speed         = base.get("speed_mhz", 3200)

    for cap_gb, price_mult in _RAM_CAPACITY_VARIANTS:
        # Normalise price relative to base capacity
        if base_capacity > 0:
            rel_mult = (cap_gb / base_capacity) * price_mult
        else:
            rel_mult = price_mult

        variant = base.copy()
        variant.update({
            "capacity_gb": cap_gb,
            "price_usd":   round(base_price * rel_mult, 2),
            "model":       re.sub(r"\d+GB", f"{cap_gb}GB", base.get("model", ""), flags=re.IGNORECASE)
                           or f"{base.get('model','')} {cap_gb}GB",
            "full_name":   re.sub(r"\d+GB", f"{cap_gb}GB", base.get("full_name", ""), flags=re.IGNORECASE),
            "id":          _make_id("RAM", base.get("brand", ""), base.get("model", ""), f"{cap_gb}GB"),
        })
        results.append(variant)
    return results


def _expand_storage_variants(base: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate capacity variants from a base storage entry."""
    results: List[Dict[str, Any]] = []
    base_price    = base.get("price_usd", 80.0)
    base_capacity = base.get("capacity_gb", 1024)
    interface     = base.get("interface", "NVMe Gen3")

    for cap_gb, price_mult in _STORAGE_CAPACITY_VARIANTS:
        # Only include HDD variants for HDD entries, SSD for SSD entries
        if "HDD" in interface and cap_gb < 512:
            continue
        if "HDD" not in interface and cap_gb < 128:
            continue

        if base_capacity > 0:
            rel_mult = (cap_gb / base_capacity) * price_mult
        else:
            rel_mult = price_mult

        cap_label = f"{cap_gb // 1024}TB" if cap_gb >= 1024 else f"{cap_gb}GB"
        variant   = base.copy()
        variant.update({
            "capacity_gb": cap_gb,
            "price_usd":   round(base_price * rel_mult, 2),
            "model":       re.sub(r"(\d+(?:GB|TB))", cap_label, base.get("model", ""), flags=re.IGNORECASE)
                           or f"{base.get('model','')} {cap_label}",
            "full_name":   re.sub(r"(\d+(?:GB|TB))", cap_label, base.get("full_name", ""), flags=re.IGNORECASE),
            "id":          _make_id("Storage", base.get("brand", ""), base.get("model", ""), cap_label),
        })
        results.append(variant)
    return results


# ─── Main Preprocessor Class ──────────────────────────────────────────────────

class Preprocessor:
    """
    Full ingestion pipeline from raw dataset → clean component list.

    The output is a list of normalised dicts ready for the MasterCatalogue.
    """

    def __init__(self, expand_gpu_variants: bool = True,
                 expand_capacity_variants: bool = True):
        self.expand_gpu = expand_gpu_variants
        self.expand_capacity = expand_capacity_variants
        self._stats: Dict[str, int] = {}

    def run(self, path: Path) -> List[Dict[str, Any]]:
        """
        Execute the full pipeline.
        Returns a list of clean, normalised component dicts.
        """
        logger.info(f"Preprocessor: loading dataset from {path}")

        # Stage 1: Load
        raw_items = _load_raw(path)
        self._stats["raw_count"] = len(raw_items)
        logger.info(f"  Loaded {len(raw_items)} raw entries")

        # Stage 2–7: Per-item processing
        normalised: List[Dict[str, Any]] = []
        seen_keys: set = set()
        dropped = {"no_type": 0, "year_filter": 0, "completeness": 0, "duplicate": 0}

        for raw in raw_items:
            # Stage 2: Resolve category
            category = _resolve_type(raw)
            if not category:
                dropped["no_type"] += 1
                continue

            # Stage 3: Year filter
            if not _passes_year_filter(raw, category):
                dropped["year_filter"] += 1
                continue

            # Stage 4: Normalise
            try:
                entry = _normalise_entry(raw, category)
            except Exception as exc:
                logger.debug(f"Normalise error: {exc} — raw: {raw}")
                continue

            # Stage 5: Completeness filter
            if not _passes_completeness(entry, category):
                dropped["completeness"] += 1
                continue

            # Stage 6: Deduplication
            dk = _dedup_key(entry)
            if dk in seen_keys:
                dropped["duplicate"] += 1
                continue
            seen_keys.add(dk)

            # Stage 7: Assign ID
            entry = _assign_id(entry)
            normalised.append(entry)

        self._stats["after_filter"] = len(normalised)
        logger.info(f"  After filtering: {len(normalised)} entries "
                    f"(dropped: {dropped})")

        # Stage 8: Variant expansion
        final: List[Dict[str, Any]] = []
        expanded_count = 0

        for entry in normalised:
            category = entry["_category"]

            if self.expand_gpu and category == "GPU":
                variants = _expand_gpu_variants(entry)
                if variants:
                    final.extend(variants)
                    expanded_count += len(variants)
                else:
                    final.append(entry)

            elif self.expand_capacity and category == "RAM":
                variants = _expand_ram_variants(entry)
                final.extend(variants)
                expanded_count += len(variants) - 1

            elif self.expand_capacity and category == "Storage":
                variants = _expand_storage_variants(entry)
                final.extend(variants)
                expanded_count += len(variants) - 1

            else:
                final.append(entry)

        self._stats["final_count"] = len(final)
        self._stats["expanded"] = expanded_count
        logger.info(f"  After variant expansion: {len(final)} entries "
                    f"({expanded_count} generated from variants)")

        return final

    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)
