"""
PCForge AI — Master Catalogue
"""
from __future__ import annotations

import logging
from typing import Any, Optional  # 🔥 ONLY SAFE IMPORTS

logger = logging.getLogger("pcforge.catalogue")


class MasterCatalogue:
    def __init__(self) -> None:
        self._components = {}       # id -> component
        self._by_category = {}      # category -> list
        self._name_index = {}
        self._loaded = False
        self._source_path = None
        self._load_result = None

    # 🔥 FIX: NO typing annotations here (THIS WAS YOUR CRASH)
    @property
    def components(self):
        return self._by_category

    # ── Lifecycle ────────────────────────────────
    def load(self, data_path):
        from backend.data.preprocessor import Preprocessor

        errors = []

        if not data_path.exists():
            result = {
                "success": False,
                "component_count": 0,
                "category_counts": {},
                "errors": [f"Dataset file not found: {data_path}"],
                "source_path": str(data_path),
            }
            self._load_result = result
            logger.warning(f"Catalogue missing at {data_path}")
            return result

        try:
            pipeline = Preprocessor()
            items = pipeline.run(data_path)

            self._components.clear()
            self._by_category.clear()
            self._name_index.clear()

            for d in items:
                try:
                    comp = d  # 🔥 keep raw dict (fix compatibility)
                    self._components[comp.get("id")] = comp
                    self._by_category.setdefault(comp.get("_category"), []).append(comp)

                    name = comp.get("full_name", "").lower()
                    model = comp.get("model", "").lower()

                    if name:
                        self._name_index[name] = comp
                    if model:
                        self._name_index[model] = comp

                except Exception as exc:
                    errors.append(str(exc))

            self._loaded = bool(self._components)
            self._source_path = str(data_path)

            cat_counts = {k: len(v) for k, v in self._by_category.items()}

            result = {
                "success": self._loaded,
                "component_count": len(self._components),
                "category_counts": cat_counts,
                "errors": errors,
                "source_path": str(data_path),
            }

            self._load_result = result

            logger.info(f"Catalogue loaded: {len(self._components)} components {cat_counts}")
            return result

        except Exception as exc:
            msg = f"Catalogue load failed: {exc}"
            logger.error(msg)

            result = {
                "success": False,
                "component_count": 0,
                "category_counts": {},
                "errors": [msg],
                "source_path": str(data_path),
            }

            self._load_result = result
            return result

    # ── Status ─────────────────────────────────
    def is_loaded(self):
        return self._loaded and bool(self._components)

    def get_load_result(self):
        return self._load_result

    def stats(self):
        return {
            "loaded": self.is_loaded(),
            "total": len(self._components),
            "categories": {k: len(v) for k, v in self._by_category.items()},
            "source": self._source_path,
        }

    # ── Query Interface ────────────────────────
    def get_by_category(self, category):
        return list(self._by_category.get(category, []))

    def get_by_id(self, component_id):
        return self._components.get(component_id)


# 🔥 SINGLETON
master_catalogue = MasterCatalogue()