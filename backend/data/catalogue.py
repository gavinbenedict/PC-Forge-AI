from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("pcforge.catalogue")


@dataclass
class CatalogueComponent:
    id: str
    category: str
    brand: str
    model: str
    full_name: str
    price_usd: float
    specs: Dict[str, Any] = field(default_factory=dict)
    year: Optional[int] = None

    @property
    def socket(self):
        return self.specs.get("socket")

    @property
    def tdp_w(self):
        return self.specs.get("tdp_w")

    @property
    def power_draw_w(self):
        return self.specs.get("power_draw_w")

    @property
    def length_mm(self):
        return self.specs.get("length_mm")

    @property
    def form_factor(self):
        return self.specs.get("form_factor")

    @property
    def ram_types(self):
        return self.specs.get("ram_types", [])

    @property
    def max_ram_gb(self):
        return self.specs.get("max_ram_gb")

    @property
    def supported_form_factors(self):
        return self.specs.get("supported_form_factors", [])

    @property
    def gpu_clearance_mm(self):
        return self.specs.get("gpu_clearance_mm")

    @property
    def cooler_clearance_mm(self):
        return self.specs.get("cooler_clearance_mm")

    @property
    def height_mm(self):
        return self.specs.get("height_mm")


def _from_dict(d: Dict[str, Any]) -> CatalogueComponent:
    top_keys = {"id", "_category", "brand", "model", "full_name", "price_usd", "year"}
    specs = {k: v for k, v in d.items() if k not in top_keys}

    return CatalogueComponent(
        id=d.get("id", ""),
        category=d.get("_category", "Unknown"),
        brand=d.get("brand", ""),
        model=d.get("model", ""),
        full_name=d.get("full_name", d.get("model", "")),
        price_usd=float(d.get("price_usd", 0.0)),
        specs=specs,
        year=d.get("year"),
    )


@dataclass
class LoadResult:
    success: bool
    component_count: int
    category_counts: Dict[str, int]
    errors: List[str]
    source_path: str


class MasterCatalogue:
    def __init__(self):
        self._components: Dict[str, CatalogueComponent] = {}
        self._by_category: Dict[str, List[CatalogueComponent]] = {}
        self._name_index: Dict[str, CatalogueComponent] = {}
        self._loaded = False
        self._source_path = None
        self._load_result = None

    @property
    def components(self):
        return self._by_category

    def load(self, data_path: Path) -> LoadResult:
        from backend.data.preprocessor import Preprocessor

        if not data_path.exists():
            result = LoadResult(
                success=False,
                component_count=0,
                category_counts={},
                errors=[f"Dataset file not found: {data_path}"],
                source_path=str(data_path),
            )
            self._load_result = result
            return result

        try:
            pipeline = Preprocessor()
            items = pipeline.run(data_path)

            self._components.clear()
            self._by_category.clear()
            self._name_index.clear()

            for d in items:
                comp = _from_dict(d)
                self._components[comp.id] = comp
                self._by_category.setdefault(comp.category, []).append(comp)
                self._name_index[comp.full_name.lower()] = comp
                self._name_index[comp.model.lower()] = comp

            self._loaded = True
            self._source_path = str(data_path)

            result = LoadResult(
                success=True,
                component_count=len(self._components),
                category_counts={k: len(v) for k, v in self._by_category.items()},
                errors=[],
                source_path=str(data_path),
            )
            self._load_result = result
            return result

        except Exception as exc:
            result = LoadResult(
                success=False,
                component_count=0,
                category_counts={},
                errors=[str(exc)],
                source_path=str(data_path),
            )
            self._load_result = result
            return result

    def is_loaded(self):
        return self._loaded

    def get_by_category(self, category: str):
        return self._by_category.get(category, [])

    def find_by_name(self, name: str, category: Optional[str] = None):
        name = name.lower()
        if name in self._name_index:
            return self._name_index[name]
        return None


master_catalogue = MasterCatalogue()