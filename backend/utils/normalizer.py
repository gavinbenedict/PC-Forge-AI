"""
PCForge AI — Input Normalizer
Converts raw user strings to canonical component names.
Falls back gracefully when catalogue is unavailable.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

# ─── Quick-lookup alias tables ────────────────────────────────────────────────
# Maps common shorthand → canonical model name used in _PRICE_DB

CPU_ALIASES: Dict[str, str] = {
    "7600x":   "AMD Ryzen 5 7600X",
    "7700x":   "AMD Ryzen 7 7700X",
    "7900x":   "AMD Ryzen 9 7900X",
    "7950x":   "AMD Ryzen 9 7950X",
    "13600k":  "Intel Core i5-13600K",
    "13700k":  "Intel Core i7-13700K",
    "13900k":  "Intel Core i9-13900K",
    "14900k":  "Intel Core i9-14900K",
    "14700k":  "Intel Core i7-14700K",
    "14600k":  "Intel Core i5-14600K",
}

GPU_ALIASES: Dict[str, str] = {
    "4060":          "NVIDIA RTX 4060",
    "4060 ti":       "NVIDIA RTX 4060 Ti",
    "4070":          "NVIDIA RTX 4070",
    "4070 super":    "NVIDIA RTX 4070 Super",
    "4070 ti":       "NVIDIA RTX 4070 Ti",
    "4070 ti super": "NVIDIA RTX 4070 Ti Super",
    "4080":          "NVIDIA RTX 4080",
    "4080 super":    "NVIDIA RTX 4080 Super",
    "4090":          "NVIDIA RTX 4090",
    "5070":          "NVIDIA RTX 5070",
    "5070 ti":       "NVIDIA RTX 5070 Ti",
    "5080":          "NVIDIA RTX 5080",
    "5090":          "NVIDIA RTX 5090",
}


# ─── String helpers ───────────────────────────────────────────────────────────

def _normalize_string(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return re.sub(r"\s+", " ", s.strip())


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ─── Fuzzy matching (catalogue-based) ────────────────────────────────────────

def find_best_match(query: str, components: List[Any]) -> Optional[Any]:
    """
    Match query string against a list of CatalogueComponent objects.
    Returns the best matching component or None.
    Gracefully handles missing rapidfuzz.
    """
    if not query or not components:
        return None

    normalized_query = normalize_text(query)

    try:
        from rapidfuzz import process, fuzz
        names = [comp.full_name for comp in components]
        normalized_names = [normalize_text(n) for n in names]
        result = process.extractOne(
            normalized_query,
            normalized_names,
            scorer=fuzz.token_sort_ratio,
        )
        if result is None:
            return None
        _, score, index = result
        if score < 70:
            return None
        return components[index]
    except Exception:
        return None


def _safe_catalogue_list(catalogue: Any, category: str) -> List[Any]:
    """
    Safely retrieve a list of CatalogueComponent from the catalogue.
    Returns [] rather than raising if the catalogue is not loaded or category missing.
    """
    if catalogue is None:
        return []
    try:
        if hasattr(catalogue, "get_by_category"):
            return catalogue.get_by_category(category) or []
        # Fallback: access internal dict directly
        comps = catalogue.components
        if isinstance(comps, dict):
            return comps.get(category, [])
    except Exception:
        pass
    return []


# ─── Component normalisers ────────────────────────────────────────────────────

def normalize_cpu(raw: Optional[str], catalogue: Any = None) -> Optional[str]:
    if not raw:
        return None

    s = _normalize_string(raw)
    if not s:
        return None

    # 1. Quick alias lookup
    lower = s.lower()
    if lower in CPU_ALIASES:
        return CPU_ALIASES[lower]

    # 2. Catalogue fuzzy match
    if catalogue:
        pool = _safe_catalogue_list(catalogue, "CPU")
        if pool:
            match = find_best_match(s, pool)
            if match:
                return match.full_name

    # 3. Pass through as-is (pricing service has its own fallback)
    return s


def normalize_gpu(raw: Optional[str], catalogue: Any = None) -> Optional[str]:
    if not raw:
        return None

    s = _normalize_string(raw)
    if not s:
        return None

    # 1. Quick alias lookup
    lower = s.lower()
    if lower in GPU_ALIASES:
        return GPU_ALIASES[lower]

    # 2. Partial alias: check if alias key appears anywhere in the string
    for key, canonical in GPU_ALIASES.items():
        if key in lower:
            return canonical

    # 3. Catalogue fuzzy match
    if catalogue:
        pool = _safe_catalogue_list(catalogue, "GPU")
        if pool:
            match = find_best_match(s, pool)
            if match:
                return match.full_name

    # 4. Pass through as-is
    return s


def normalize_motherboard(raw: Optional[str], catalogue: Any = None) -> Optional[str]:
    if not raw:
        return None
    s = _normalize_string(raw)
    if not s:
        return None
    if catalogue:
        pool = _safe_catalogue_list(catalogue, "Motherboard")
        if pool:
            match = find_best_match(s, pool)
            if match:
                return match.full_name
    return s


# ─── Main pipeline ────────────────────────────────────────────────────────────

def normalize_build_spec(raw_spec: Dict[str, Any], catalogue: Any = None) -> Dict[str, Any]:
    spec = dict(raw_spec)

    if spec.get("cpu"):
        spec["cpu"] = normalize_cpu(spec["cpu"], catalogue)

    if spec.get("gpu"):
        spec["gpu"] = normalize_gpu(spec["gpu"], catalogue)

    if spec.get("motherboard"):
        spec["motherboard"] = normalize_motherboard(spec["motherboard"], catalogue)

    return spec