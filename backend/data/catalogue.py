"""
PCForge AI — Master Catalogue
==============================
A typed, queryable singleton that serves as the single source of truth
for all component data. Services read from here; never from raw data.

Lifecycle:
  - On startup: catalogue.load(path) is called by app.py lifespan
  - If no dataset is found: catalogue remains empty, services fall back to
    their built-in data (compatibility_rules.json + hardcoded lists)
  - Once loaded: provides fast lookups via name-index and category-index

Usage:
    from backend.data.catalogue import master_catalogue
    cpus = master_catalogue.get_by_category("CPU")
    socket = master_catalogue.get_cpu_socket("Intel Core i5-12600K")
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("pcforge.catalogue")


# ─── Component Data Class ─────────────────────────────────────────────────────

@dataclass
class CatalogueComponent:
    id:        str
    category:  str           # CPU | GPU | Motherboard | RAM | Storage | PSU | Case | Cooler
    brand:     str
    model:     str
    full_name: str
    price_usd: float
    specs:     Dict[str, Any] = field(default_factory=dict)
    year:      Optional[int] = None

    # ── Convenience accessors (thin wrappers over specs) ─────────────────────

    # CPU
    @property
    def socket(self) -> Optional[str]:
        return self.specs.get("socket")

    @property
    def cores(self) -> Optional[int]:
        return self.specs.get("cores")

    @property
    def tdp_w(self) -> Optional[int]:
        return self.specs.get("tdp_w")

    @property
    def generation(self) -> Optional[int]:
        return self.specs.get("generation")

    # GPU
    @property
    def vram_gb(self) -> Optional[int]:
        return self.specs.get("vram_gb")

    @property
    def power_draw_w(self) -> Optional[int]:
        return self.specs.get("power_draw_w")

    @property
    def length_mm(self) -> Optional[int]:
        return self.specs.get("length_mm")

    # Motherboard
    @property
    def chipset(self) -> Optional[str]:
        return self.specs.get("chipset")

    @property
    def form_factor(self) -> Optional[str]:
        return self.specs.get("form_factor")

    @property
    def ram_types(self) -> List[str]:
        return self.specs.get("ram_types", [])

    @property
    def max_ram_gb(self) -> Optional[int]:
        return self.specs.get("max_ram_gb")

    # RAM
    @property
    def capacity_gb(self) -> Optional[int]:
        return self.specs.get("capacity_gb")

    @property
    def ram_type(self) -> Optional[str]:
        return self.specs.get("ram_type")

    @property
    def speed_mhz(self) -> Optional[int]:
        return self.specs.get("speed_mhz")

    # Storage
    @property
    def interface(self) -> Optional[str]:
        return self.specs.get("interface")

    # PSU
    @property
    def wattage_w(self) -> Optional[int]:
        return self.specs.get("wattage_w")

    @property
    def efficiency(self) -> Optional[str]:
        return self.specs.get("efficiency")

    # Case
    @property
    def supported_form_factors(self) -> List[str]:
        return self.specs.get("supported_form_factors", [])

    @property
    def gpu_clearance_mm(self) -> Optional[int]:
        return self.specs.get("gpu_clearance_mm")

    @property
    def cooler_clearance_mm(self) -> Optional[int]:
        return self.specs.get("cooler_clearance_mm")

    # Cooler
    @property
    def cooler_type(self) -> Optional[str]:
        return self.specs.get("cooler_type")

    @property
    def tdp_rating_w(self) -> Optional[int]:
        return self.specs.get("tdp_rating_w")

    @property
    def height_mm(self) -> Optional[int]:
        return self.specs.get("height_mm")

    @property
    def is_aio(self) -> bool:
        return self.specs.get("is_aio", False)


def _from_dict(d: Dict[str, Any]) -> CatalogueComponent:
    """Build a CatalogueComponent from a preprocessor output dict."""
    # Pull top-level fields out, rest goes into specs
    top_keys = {"id", "_category", "brand", "model", "full_name", "price_usd", "year"}
    specs = {k: v for k, v in d.items() if k not in top_keys}

    return CatalogueComponent(
        id        = d.get("id", ""),
        category  = d.get("_category", "Unknown"),
        brand     = d.get("brand", ""),
        model     = d.get("model", ""),
        full_name = d.get("full_name", d.get("model", "")),
        price_usd = float(d.get("price_usd", 0.0)),
        specs     = specs,
        year      = d.get("year"),
    )


# ─── Load Result ──────────────────────────────────────────────────────────────

@dataclass
class LoadResult:
    success:       bool
    component_count: int
    category_counts: Dict[str, int]
    errors:        List[str]
    source_path:   Optional[str] = None


# ─── Token-based Fuzzy Matching ─────────────────────────────────────────────

def _tokenize(s: str) -> List[str]:
    """Split a component name into meaningful lowercase tokens."""
    noise = {"the", "a", "an", "and", "or", "with", "for", "by", "in", "of"}
    tokens = re.findall(r"[a-z0-9]+", s.lower())
    return [t for t in tokens if t not in noise and len(t) >= 2]


def _token_score(query_tokens: List[str], name_tokens: List[str]) -> float:
    """Score [0,1] token overlap between query and candidate."""
    if not query_tokens:
        return 0.0
    matches = sum(1 for qt in query_tokens
                  if any(qt in nt or nt in qt for nt in name_tokens))
    return matches / len(query_tokens)


def _critical_tokens(s: str) -> set:
    """
    Extract tokens that uniquely identify a model and must match exactly.
    Rules:
      - Pure numbers with 3+ digits: 9600, 7900, 4090, 650, 790 …
      - Alphanumeric tokens where the digit portion is 3+ digits: rtx4090, b650
      - Suffix letters directly attached to a number: 9600X, 7800XT, 6950XT
    These tokens must ALL appear in the candidate for a match to be valid.
    """
    critical = set()
    # Find standalone numbers ≥ 3 digits  (e.g. "9600", "4090", "650")
    for m in re.finditer(r'\b(\d{3,})\b', s.lower()):
        critical.add(m.group(1))
    # Find alphanumeric model tokens with 3+ digit run (e.g. "rtx4090", "b650")
    for m in re.finditer(r'[a-z]*\d{3,}[a-z]*', s.lower()):
        critical.add(m.group())
    # Find number+suffix combos (e.g. "9600x", "7800xt")
    for m in re.finditer(r'(\d{3,})([a-z]{1,3})\b', s.lower()):
        critical.add(m.group())    # whole token, e.g. "9600x"
        critical.add(m.group(1))   # bare number, e.g. "9600"
    return critical


# ─── Match Result ─────────────────────────────────────────────────────────────

@dataclass
class MatchResult:
    """
    Returned by resolve_user_component().
    is_substitution=True means the exact model was NOT found and a similar
    component was used as a fallback — callers MUST surface a warning.
    """
    component:       Optional["CatalogueComponent"]
    is_exact:        bool          # True  → strict exact/critical-token match
    is_substitution: bool          # True  → fallback used, warn the user
    matched_name:    Optional[str] # What name was actually matched
    warning:         Optional[str] # Human-readable substitution warning



# ─── Master Catalogue Singleton ───────────────────────────────────────────────

class MasterCatalogue:
    """
    The single source of truth for all PC components.

    Data is populated by calling .load(path) on app startup.
    If not loaded, all query methods return empty results, and services
    automatically fall back to their built-in data.
    """

    def __init__(self) -> None:
        self._components: Dict[str, CatalogueComponent] = {}   # id → component
        self._by_category: Dict[str, List[CatalogueComponent]] = {}
        self._name_index: Dict[str, CatalogueComponent] = {}   # full_name.lower() → component
        self._loaded: bool = False
        self._source_path: Optional[str] = None
        self._load_result: Optional[LoadResult] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def load(self, data_path: Path) -> LoadResult:
        """
        Load and preprocess dataset from disk.
        Safe to call multiple times (reloads each time).
        """
        from backend.data.preprocessor import Preprocessor

        errors: List[str] = []

        if not data_path.exists():
            result = LoadResult(
                success=False,
                component_count=0,
                category_counts={},
                errors=[f"Dataset file not found: {data_path}"],
                source_path=str(data_path),
            )
            self._load_result = result
            logger.warning(f"Catalogue: dataset not found at {data_path}. "
                           "Services will use built-in fallback data.")
            return result

        try:
            pipeline = Preprocessor()
            items    = pipeline.run(data_path)

            self._components.clear()
            self._by_category.clear()
            self._name_index.clear()

            for d in items:
                try:
                    comp = _from_dict(d)
                    self._components[comp.id] = comp
                    self._by_category.setdefault(comp.category, []).append(comp)
                    # Index by full name and model
                    self._name_index[comp.full_name.lower()] = comp
                    self._name_index[comp.model.lower()] = comp
                except Exception as exc:
                    errors.append(str(exc))

            self._loaded = bool(self._components)
            self._source_path = str(data_path)
            cat_counts = {k: len(v) for k, v in self._by_category.items()}

            result = LoadResult(
                success=self._loaded,
                component_count=len(self._components),
                category_counts=cat_counts,
                errors=errors,
                source_path=str(data_path),
            )
            self._load_result = result

            logger.info(
                f"Catalogue loaded: {len(self._components)} components "
                f"({cat_counts})"
            )
            return result

        except Exception as exc:
            msg = f"Catalogue load failed: {exc}"
            logger.error(msg)
            result = LoadResult(
                success=False,
                component_count=0,
                category_counts={},
                errors=[msg],
                source_path=str(data_path),
            )
            self._load_result = result
            return result

    # ── Status ────────────────────────────────────────────────────────────────

    def is_loaded(self) -> bool:
        """True if dataset was successfully loaded and has entries."""
        return self._loaded and bool(self._components)

    def get_load_result(self) -> Optional[LoadResult]:
        return self._load_result

    def stats(self) -> Dict[str, Any]:
        return {
            "loaded":     self.is_loaded(),
            "total":      len(self._components),
            "categories": {k: len(v) for k, v in self._by_category.items()},
            "source":     self._source_path,
        }

    # ── Query Interface ───────────────────────────────────────────────────────

    def get_by_category(self, category: str) -> List[CatalogueComponent]:
        """Return all components in a category. Empty list if not loaded."""
        return list(self._by_category.get(category, []))

    def get_by_id(self, component_id: str) -> Optional[CatalogueComponent]:
        return self._components.get(component_id)

    def find_by_name(
        self,
        name: str,
        category: Optional[str] = None,
        threshold: float = 0.75,
    ) -> Optional["CatalogueComponent"]:
        """
        Find a component by name (used internally by services for auto-fill).
        Resolution order: exact → critical-token-safe substring → token-overlap.

        ⚠️  For USER-PROVIDED components use resolve_user_component() instead —
        it returns a MatchResult with substitution warnings.
        """
        result = self.resolve_user_component(name, category, threshold)
        return result.component

    def resolve_user_component(
        self,
        name: str,
        category: Optional[str] = None,
        threshold: float = 0.75,
    ) -> "MatchResult":
        """
        Safe resolution for user-supplied component names.

        Returns a MatchResult with:
          is_exact=True      → strict match, use with no warning.
          is_substitution=True → closest fuzzy match used; caller MUST warn user.
          component=None     → no match found in catalogue.

        Algorithm (strict-first, hard-blocked on model numbers):
          1. Case-insensitive full-string exact match.
          2. Normalised exact match (strip punctuation/extra spaces).
          3. Substring match — query MUST be a prefix/substring of candidate,
             AND all critical tokens must match exactly.
          4. Token-overlap fallback — critical token mismatch is a HARD BLOCK
             (not a soft penalty). Flagged is_substitution=True.
        """
        if not self.is_loaded():
            return MatchResult(None, False, False, None, None)

        name_stripped  = name.strip()
        name_lower     = name_stripped.lower()
        query_critical = _critical_tokens(name_lower)

        pool: List[CatalogueComponent] = (
            list(self._by_category.get(category, []))
            if category
            else list(self._components.values())
        )

        # ── 1. Exact match (case-insensitive) ─────────────────────────────────
        direct = self._name_index.get(name_lower)
        if direct and (category is None or direct.category == category):
            return MatchResult(direct, True, False, direct.full_name, None)

        # Normalised exact: collapse punctuation + spaces
        def _norm(s: str) -> str:
            return re.sub(r'[^a-z0-9]', '', s.lower())

        norm_query = _norm(name_lower)
        for key, comp in self._name_index.items():
            if category and comp.category != category:
                continue
            if _norm(key) == norm_query:
                return MatchResult(comp, True, False, comp.full_name, None)

        # ── 2. Substring match — query IN candidate only (not reverse) ─────────
        # Reverse substring would allow short wrong names to match long correct ones.
        for comp in pool:
            cand_lower    = comp.full_name.lower()
            cand_critical = _critical_tokens(cand_lower)
            if name_lower in cand_lower:
                # All query critical tokens must be present in candidate
                if not query_critical or query_critical <= cand_critical:
                    return MatchResult(comp, True, False, comp.full_name, None)

        # ── 3. Token-overlap fallback (substitution, last resort) ─────────────
        # HARD RULE: if the query has any critical token (model number/chipset)
        # that is NOT found in the candidate, that candidate is SKIPPED entirely.
        # This prevents 9600X → 7600X, X870E → Z790, etc.
        query_tokens = _tokenize(name)
        best_score, best_comp = 0.0, None

        for comp in pool:
            cand_tokens   = _tokenize(comp.full_name)
            cand_critical = _critical_tokens(comp.full_name.lower())

            # Hard block — critical token mismatch: skip, do NOT score
            if query_critical and not query_critical.issubset(
                cand_critical | set(cand_tokens)
            ):
                continue

            score = _token_score(query_tokens, cand_tokens)
            if score > best_score:
                best_score = score
                best_comp  = comp

        if best_comp and best_score >= threshold:
            warning = (
                f"Exact component '{name_stripped}' not found in dataset. "
                f"Using closest match: '{best_comp.full_name}'. "
                "Verify this is correct — the exact model was not in the catalogue."
            )
            logger.warning(
                "Component substitution: '%s' → '%s' (score=%.2f)",
                name_stripped, best_comp.full_name, best_score,
            )
            return MatchResult(best_comp, False, True, best_comp.full_name, warning)

        # No acceptable match — return explicit not-found
        logger.info(
            "No catalogue match for '%s' (category=%s) — component not found.",
            name, category,
        )
        return MatchResult(None, False, False, None,
            f"Component '{name_stripped}' not found in catalogue."
        )



    def find_many(
        self,
        category: str,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "price_usd",
        limit: int = 50,
    ) -> List[CatalogueComponent]:
        """
        Query components with optional spec filters and sorting.

        filters example:
            {"socket": "LGA1700", "ram_types__contains": "DDR5"}

        Supports operators: __gte, __lte, __contains, __in
        """
        pool = self.get_by_category(category)
        if filters:
            pool = [c for c in pool if _matches_filters(c, filters)]
        pool.sort(key=lambda c: getattr(c, sort_by, 0) or c.price_usd)
        return pool[:limit]

    # ── compatibility-specific lookups ────────────────────────────────────────

    def get_cpu_socket(self, cpu_name: str) -> Optional[str]:
        comp = self.find_by_name(cpu_name, "CPU")
        return comp.socket if comp else None

    def get_cpu_tdp(self, cpu_name: str) -> Optional[int]:
        comp = self.find_by_name(cpu_name, "CPU")
        return comp.tdp_w if comp else None

    def get_mb_socket(self, mb_name: str) -> Optional[str]:
        comp = self.find_by_name(mb_name, "Motherboard")
        return comp.socket if comp else None

    def get_mb_chipset(self, mb_name: str) -> Optional[str]:
        comp = self.find_by_name(mb_name, "Motherboard")
        return comp.chipset if comp else None

    def get_mb_ram_types(self, mb_name: str) -> List[str]:
        comp = self.find_by_name(mb_name, "Motherboard")
        return comp.ram_types if comp else []

    def get_mb_form_factor(self, mb_name: str) -> Optional[str]:
        comp = self.find_by_name(mb_name, "Motherboard")
        return comp.form_factor if comp else None

    def get_mb_max_ram(self, mb_name: str) -> Optional[int]:
        comp = self.find_by_name(mb_name, "Motherboard")
        return comp.max_ram_gb if comp else None

    def get_gpu_length(self, gpu_name: str) -> Optional[int]:
        comp = self.find_by_name(gpu_name, "GPU")
        return comp.length_mm if comp else None

    def get_gpu_tdp(self, gpu_name: str) -> Optional[int]:
        comp = self.find_by_name(gpu_name, "GPU")
        return comp.power_draw_w if comp else None

    def get_case_gpu_clearance(self, case_name: str) -> Optional[int]:
        comp = self.find_by_name(case_name, "Case")
        return comp.gpu_clearance_mm if comp else None

    def get_case_cooler_clearance(self, case_name: str) -> Optional[int]:
        comp = self.find_by_name(case_name, "Case")
        return comp.cooler_clearance_mm if comp else None

    def get_case_form_factors(self, case_name: str) -> List[str]:
        comp = self.find_by_name(case_name, "Case")
        return comp.supported_form_factors if comp else []

    def get_cooler_height(self, cooler_name: str) -> Optional[int]:
        comp = self.find_by_name(cooler_name, "Cooler")
        return comp.height_mm if comp else None

    def get_price(self, name: str, category: Optional[str] = None) -> Optional[float]:
        comp = self.find_by_name(name, category)
        return comp.price_usd if comp else None


# ─── Filter Helper ────────────────────────────────────────────────────────────

def _matches_filters(comp: CatalogueComponent, filters: Dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if "__" in key:
            field_name, op = key.rsplit("__", 1)
        else:
            field_name, op = key, "eq"

        # Resolve value from specs or top-level attributes
        actual = comp.specs.get(field_name) or getattr(comp, field_name, None)

        if op == "eq" and actual != expected:
            return False
        elif op == "gte" and (actual is None or actual < expected):
            return False
        elif op == "lte" and (actual is None or actual > expected):
            return False
        elif op == "contains" and (actual is None or expected not in actual):
            return False
        elif op == "in" and (actual is None or actual not in expected):
            return False

    return True


# ─── Module-level Singleton ───────────────────────────────────────────────────

master_catalogue = MasterCatalogue()
