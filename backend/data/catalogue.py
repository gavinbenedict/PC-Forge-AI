class MasterCatalogue:
    def __init__(self) -> None:
        self._components: Dict[str, CatalogueComponent] = {}
        self._by_category: Dict[str, List[CatalogueComponent]] = {}
        self._name_index: Dict[str, CatalogueComponent] = {}
        self._loaded: bool = False
        self._source_path: Optional[str] = None
        self._load_result: Optional[LoadResult] = None

    # 🔥 COMPATIBILITY FIX (DO NOT TOUCH THIS AGAIN)
    @property
    def components(self) -> Dict[str, List[CatalogueComponent]]:
        return self._by_category

    # ── Lifecycle ────────────────────────────────

    def load(self, data_path: Path) -> LoadResult:
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
            logger.warning("Dataset not found — fallback mode")
            return result

        try:
            pipeline = Preprocessor()
            items = pipeline.run(data_path)

            self._components.clear()
            self._by_category.clear()
            self._name_index.clear()

            for d in items:
                try:
                    comp = _from_dict(d)
                    self._components[comp.id] = comp
                    self._by_category.setdefault(comp.category, []).append(comp)
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

            logger.info(f"Catalogue loaded: {len(self._components)} components ({cat_counts})")

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

    # ── Status ─────────────────────────────────

    def is_loaded(self) -> bool:
        return self._loaded and bool(self._components)

    def get_load_result(self) -> Optional[LoadResult]:
        return self._load_result

    def stats(self) -> Dict[str, Any]:
        return {
            "loaded": self.is_loaded(),
            "total": len(self._components),
            "categories": {k: len(v) for k, v in self._by_category.items()},
            "source": self._source_path,
        }

    # ── Query ─────────────────────────────────

    def get_by_category(self, category: str) -> List[CatalogueComponent]:
        return list(self._by_category.get(category, []))

    def get_by_id(self, component_id: str) -> Optional[CatalogueComponent]:
        return self._components.get(component_id)