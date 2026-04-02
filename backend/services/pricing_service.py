from __future__ import annotations
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.models.schemas import PricedPart

logger = logging.getLogger(__name__)

# ─── PRICE DATABASE (MIN SAFE VERSION) ─────────────────────────────
# ⚠️ Replace this later with your full DB if you want
_PRICE_DB: Dict[str, Dict[str, Any]] = {
    "NVIDIA RTX 4090": {"price": 1599.99, "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA RTX 4060": {"price": 299.99, "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "AMD Ryzen 5 7600": {"price": 149.99, "brand": "AMD", "category": "CPU", "store": "Amazon"},
    "Intel Core i5-13600K": {"price": 219.99, "brand": "Intel", "category": "CPU", "store": "Newegg"},
}

# ─── STORE URL MAP ────────────────────────────────────────────────

_STORE_URL_MAP = {
    "Amazon":       "https://www.amazon.com/s?k={}",
    "Newegg":       "https://www.newegg.com/p/pl?d={}",
    "Best Buy":     "https://www.bestbuy.com/site/searchpage.jsp?st={}",
    "B&H Photo":    "https://www.bhphotovideo.com/c/search?q={}",
    "Micro Center": "https://www.microcenter.com/search/search_results.aspx?Ntt={}",
}

def _build_url(model: str, store: str) -> str:
    template = _STORE_URL_MAP.get(store, "https://www.google.com/search?q={}")
    return template.format(model.replace(" ", "+"))

def _add_price_jitter(base_price: float, pct: float = 0.03) -> float:
    jitter = base_price * pct
    return round(random.uniform(base_price - jitter, base_price + jitter), 2)

# ─── PRICING SERVICE ─────────────────────────────────────────────

class PricingService:

    def get_price(self, model: str, category: str) -> Optional[PricedPart]:

        # 🧠 SAFE ACCESS (NO CRASH EVEN IF DB BROKEN)
        if "_PRICE_DB" not in globals():
            logger.error("_PRICE_DB missing — using emergency fallback")
            return self._fallback_price(model, category)

        # ───────────── HARD DB LOOKUP ─────────────
        data = _PRICE_DB.get(model)
        if data:
            return self._build_priced_part(model, data)

        # ───────────── PARTIAL MATCH ─────────────
        import re as _re

        def _num_tokens(s: str):
            return set(_re.findall(r'\d{3,}[a-z]*', s.lower()))

        query_nums = _num_tokens(model)

        for db_model, db_data in _PRICE_DB.items():
            if db_data["category"] != category:
                continue

            cand_nums = _num_tokens(db_model)

            if query_nums and not query_nums.issubset(cand_nums):
                continue

            q_words = {w.lower() for w in model.split() if len(w) > 3 and not w.isdigit()}
            c_words = {w.lower() for w in db_model.split() if len(w) > 3 and not w.isdigit()}

            if q_words & c_words:
                return self._build_priced_part(db_model, db_data)

        # ───────────── CATALOGUE FALLBACK ─────────────
        try:
            from backend.data.catalogue import master_catalogue

            if master_catalogue.is_loaded():
                comp = master_catalogue.find_by_name(model, category)

                if comp:
                    price = comp.price_usd

                    if not price or price <= 0:
                        price = self._fallback_price_value(category)

                    store = _PRICE_DB.get(comp.full_name, {}).get("store", "Newegg")

                    return PricedPart(
                        category=comp.category,
                        brand=comp.brand,
                        model=comp.full_name,
                        price_usd=_add_price_jitter(price),
                        currency="USD",
                        store=store,
                        availability="In Stock",
                        url=_build_url(comp.full_name, store),
                        last_updated=datetime.now(timezone.utc),
                        source="simulated",
                    )

        except Exception as exc:
            logger.error("Catalogue failed: %s", exc)

        # ───────────── FINAL FALLBACK ─────────────
        return self._fallback_price(model, category)

    # ───────────── HELPERS ─────────────

    def _build_priced_part(self, model: str, data: Dict[str, Any]) -> PricedPart:
        return PricedPart(
            category=data["category"],
            brand=data["brand"],
            model=model,
            price_usd=_add_price_jitter(data["price"]),
            currency="USD",
            store=data["store"],
            availability="In Stock",
            url=_build_url(model, data["store"]),
            last_updated=datetime.now(timezone.utc),
            source="simulated",
        )

    def _fallback_price_value(self, category: str) -> float:
        fallback_prices = {
            "CPU": 250,
            "GPU": 800,
            "Motherboard": 200,
            "RAM": 100,
            "Storage": 120,
            "PSU": 110,
            "Case": 130,
            "Cooler": 80,
        }
        return fallback_prices.get(category, 50)

    def _fallback_price(self, model: str, category: str) -> PricedPart:
        return PricedPart(
            category=category,
            brand="Unknown",
            model=model,
            price_usd=_add_price_jitter(self._fallback_price_value(category)),
            currency="USD",
            store="Estimated",
            availability="Unknown",
            url=_build_url(model, "Amazon"),
            last_updated=datetime.now(timezone.utc),
            source="fallback",
        )

    def get_all_by_category(self, category: str) -> List[PricedPart]:
        results = []

        for model, data in _PRICE_DB.items():
            if data["category"] == category:
                results.append(self._build_priced_part(model, data))

        return results

    def get_base_price(self, model: str) -> Optional[float]:
        data = _PRICE_DB.get(model)
        return data["price"] if data else None


# ─── SINGLETON ─────────────────────────────────────────────

pricing_service = PricingService()