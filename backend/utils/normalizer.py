"""
PCForge AI — Input Normalizer + Fuzzy Matching (FIXED)
"""
from __future__ import annotations
import re
from typing import Any, Dict, Optional, List
from rapidfuzz import process, fuzz


# ─────────────────────────────────────────────────────────────
# ALIASES
# ─────────────────────────────────────────────────────────────

CPU_ALIASES = {
    "7600x": "AMD Ryzen 5 7600X",
    "7700x": "AMD Ryzen 7 7700X",
    "7900x": "AMD Ryzen 9 7900X",
    "7950x": "AMD Ryzen 9 7950X",
    "13600k": "Intel Core i5-13600K",
    "13700k": "Intel Core i7-13700K",
    "13900k": "Intel Core i9-13900K",
}

GPU_ALIASES = {
    "4060 ti": "NVIDIA RTX 4060 Ti",
    "4070": "NVIDIA RTX 4070",
    "4080": "NVIDIA RTX 4080",
    "4090": "NVIDIA RTX 4090",
}


# ─────────────────────────────────────────────────────────────
# BASIC NORMALIZATION
# ─────────────────────────────────────────────────────────────

def _normalize_string(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return re.sub(r"\s+", " ", s.strip())


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ─────────────────────────────────────────────────────────────
# 🔥 FIXED FUZZY MATCHING (NOW WORKS WITH CatalogueComponent)
# ─────────────────────────────────────────────────────────────

def find_best_match(query: str, components: List[Any]):
    """
    components = List[CatalogueComponent]
    """
    if not query or not components:
        return None

    normalized_query = normalize_text(query)

    # Extract names from objects
    names = [comp.full_name for comp in components]
    normalized_names = [normalize_text(name) for name in names]

    result = process.extractOne(
        normalized_query,
        normalized_names,
        scorer=fuzz.token_sort_ratio
    )

    if result is None:
        return None

    _, score, index = result

    if score < 70:
        return None

    return components[index]   # RETURN OBJECT


# ─────────────────────────────────────────────────────────────
# CPU NORMALIZATION
# ─────────────────────────────────────────────────────────────

def normalize_cpu(raw: Optional[str], catalogue=None):
    if not raw:
        return None

    s = _normalize_string(raw).lower()

    if s in CPU_ALIASES:
        return CPU_ALIASES[s]

    if catalogue:
        match = find_best_match(raw, catalogue.components["CPU"])
        if match:
            return match.full_name   # FIXED

    return raw.strip()


# ─────────────────────────────────────────────────────────────
# GPU NORMALIZATION
# ─────────────────────────────────────────────────────────────

def normalize_gpu(raw: Optional[str], catalogue=None):
    if not raw:
        return None

    s = _normalize_string(raw).lower()

    if s in GPU_ALIASES:
        return GPU_ALIASES[s]

    if catalogue:
        match = find_best_match(raw, catalogue.components["GPU"])
        if match:
            return match.full_name   # FIXED

    return raw.strip()


# ─────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────

def normalize_build_spec(raw_spec: Dict[str, Any], catalogue=None) -> Dict[str, Any]:
    spec = dict(raw_spec)

    if spec.get("cpu"):
        spec["cpu"] = normalize_cpu(spec["cpu"], catalogue)

    if spec.get("gpu"):
        spec["gpu"] = normalize_gpu(spec["gpu"], catalogue)

    if spec.get("motherboard") and catalogue:
        match = find_best_match(
            spec["motherboard"],
            catalogue.components["Motherboard"]
        )
        if match:
            spec["motherboard"] = match.full_name   # FIXED

    return spec