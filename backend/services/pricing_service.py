from __future__ import annotations
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.models.schemas import PricedPart

logger = logging.getLogger(__name__)

# ─── PRICE DATABASE ──────────────────────────────────────────────────────────
# KEEP YOUR EXISTING _PRICE_DB EXACTLY AS IS (DO NOT MODIFY IT)
# I'm not repeating it here to save your sanity — leave it untouched

# ─── STORE URL MAP ────────────────────────────────────────────────────────────

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


# ─── PRICING SERVICE ─────────────────────────────────────────────────────────

class PricingService:

    def get_price(self, model: str, category: str) -> Optional[PricedPart]:
        """
        FIXED ORDER:
        1. _PRICE_DB (REALISTIC PRICES)
        2. Catalogue (fallback)
        """

        # ───────────── 1. HARD DB FIRST (IMPORTANT FIX) ─────────────
        data = _PRICE_DB.get(model)
        if data:
            return self._build_priced_part(model, data)

        # strict partial match
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

        # ───────────── 2. FALLBACK TO CATALOGUE ─────────────
        try:
            from backend.data.catalogue import master_catalogue

            if master_catalogue.is_loaded():
                comp = master_catalogue.find_by_name(model, category)

                if comp:
                    price = comp.price_usd
                    name = comp.full_name.lower()

                    # 🔥 GPU sanity correction
                    if comp.category == "GPU":
                        if "5090" in name:
                            price = max(price, 1800)
                        elif "4090" in name:
                            price = max(price, 1500)
                        elif "4080" in name:
                            price = max(price, 1000)

                    # 🔥 fallback pricing if missing / zero
                    if not price or price <= 0:
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
                        price = fallback_prices.get(comp.category, 50)

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
            logger.debug("Catalogue fallback failed: %s", exc)

        return None


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


    def get_all_by_category(self, category: str) -> List[PricedPart]:
        results = []

        try:
            from backend.data.catalogue import master_catalogue

            if master_catalogue.is_loaded():
                for comp in master_catalogue.get_by_category(category):

                    price = comp.price_usd

                    if not price or price <= 0:
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
                        price = fallback_prices.get(comp.category, 50)

                    store = _PRICE_DB.get(comp.full_name, {}).get("store", "Newegg")

                    results.append(PricedPart(
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
                    ))

                if results:
                    return results

        except Exception:
            pass

        for model, data in _PRICE_DB.items():
            if data["category"] == category:
                results.append(self._build_priced_part(model, data))

        return results


    def get_base_price(self, model: str) -> Optional[float]:
        data = _PRICE_DB.get(model)
        return data["price"] if data else None


# ─── SINGLETON ───────────────────────────────────────────────────────────────

pricing_service = PricingService()