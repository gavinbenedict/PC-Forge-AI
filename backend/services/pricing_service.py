from __future__ import annotations
import logging
import random
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.models.schemas import PricedPart

logger = logging.getLogger(__name__)

# ─── Price Database ───────────────────────────────────────────────────────────

_PRICE_DB: Dict[str, Dict[str, Any]] = {
    # CPUs
    "AMD Ryzen 9 7950X":        {"price": 549.99,  "brand": "AMD",   "category": "CPU", "store": "Newegg"},
    "AMD Ryzen 9 7900X":        {"price": 349.99,  "brand": "AMD",   "category": "CPU", "store": "Amazon"},
    "AMD Ryzen 9 7900":         {"price": 299.99,  "brand": "AMD",   "category": "CPU", "store": "Micro Center"},
    "AMD Ryzen 7 7700X":        {"price": 249.99,  "brand": "AMD",   "category": "CPU", "store": "Best Buy"},
    "AMD Ryzen 7 7700":         {"price": 199.99,  "brand": "AMD",   "category": "CPU", "store": "Newegg"},
    "AMD Ryzen 5 7600X":        {"price": 169.99,  "brand": "AMD",   "category": "CPU", "store": "Amazon"},
    "AMD Ryzen 5 7600":         {"price": 149.99,  "brand": "AMD",   "category": "CPU", "store": "Micro Center"},
    "AMD Ryzen 9 5950X":        {"price": 349.99,  "brand": "AMD",   "category": "CPU", "store": "Newegg"},
    "AMD Ryzen 9 5900X":        {"price": 249.99,  "brand": "AMD",   "category": "CPU", "store": "Amazon"},
    "AMD Ryzen 7 5800X3D":      {"price": 229.99,  "brand": "AMD",   "category": "CPU", "store": "Amazon"},
    "AMD Ryzen 5 5600X":        {"price": 129.99,  "brand": "AMD",   "category": "CPU", "store": "Newegg"},
    "AMD Ryzen 5 5600":         {"price": 99.99,   "brand": "AMD",   "category": "CPU", "store": "Micro Center"},
    "AMD Ryzen 9 9950X":        {"price": 649.99,  "brand": "AMD",   "category": "CPU", "store": "Amazon"},
    "AMD Ryzen 9 9900X":        {"price": 449.99,  "brand": "AMD",   "category": "CPU", "store": "Newegg"},
    "AMD Ryzen 7 9700X":        {"price": 329.99,  "brand": "AMD",   "category": "CPU", "store": "Amazon"},
    "AMD Ryzen 5 9600X":        {"price": 249.99,  "brand": "AMD",   "category": "CPU", "store": "Newegg"},
    "Intel Core i9-14900K":     {"price": 569.99,  "brand": "Intel", "category": "CPU", "store": "B&H Photo"},
    "Intel Core i9-14900KF":    {"price": 529.99,  "brand": "Intel", "category": "CPU", "store": "Newegg"},
    "Intel Core i7-14700K":     {"price": 389.99,  "brand": "Intel", "category": "CPU", "store": "Amazon"},
    "Intel Core i5-14600K":     {"price": 249.99,  "brand": "Intel", "category": "CPU", "store": "Best Buy"},
    "Intel Core i9-13900K":     {"price": 469.99,  "brand": "Intel", "category": "CPU", "store": "Amazon"},
    "Intel Core i7-13700K":     {"price": 329.99,  "brand": "Intel", "category": "CPU", "store": "Newegg"},
    "Intel Core i5-13600K":     {"price": 219.99,  "brand": "Intel", "category": "CPU", "store": "Amazon"},
    "Intel Core i5-13400F":     {"price": 159.99,  "brand": "Intel", "category": "CPU", "store": "Micro Center"},
    "Intel Core i9-12900K":     {"price": 299.99,  "brand": "Intel", "category": "CPU", "store": "Amazon"},
    "Intel Core i5-12600K":     {"price": 179.99,  "brand": "Intel", "category": "CPU", "store": "Newegg"},
    "Intel Core i5-12400F":     {"price": 129.99,  "brand": "Intel", "category": "CPU", "store": "Amazon"},

    # GPUs
    "NVIDIA RTX 5090":              {"price": 1999.99, "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA RTX 5080":              {"price": 1199.99, "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 5070 Ti":           {"price": 849.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 5070":              {"price": 649.99,  "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA RTX 5060 Ti":           {"price": 429.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 4090":              {"price": 1599.99, "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA RTX 4080 Super":        {"price": 999.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 4080":              {"price": 899.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 4070 Ti Super":     {"price": 799.99,  "brand": "NVIDIA", "category": "GPU", "store": "B&H Photo"},
    "NVIDIA RTX 4070 Ti":           {"price": 749.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 4070 Super":        {"price": 599.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 4070":              {"price": 549.99,  "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA RTX 4060 Ti":           {"price": 399.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 4060":              {"price": 299.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 3090":              {"price": 699.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 3080 Ti":           {"price": 549.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 3080":              {"price": 449.99,  "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA RTX 3070":              {"price": 299.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 3060":              {"price": 199.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA GeForce RTX 5090":      {"price": 1999.99, "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA GeForce RTX 5080":      {"price": 1199.99, "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA GeForce RTX 5070 Ti":   {"price": 849.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA GeForce RTX 5070":      {"price": 649.99,  "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA GeForce RTX 5060 Ti":   {"price": 429.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA GeForce RTX 4090":      {"price": 1599.99, "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA GeForce RTX 4080 Super":{"price": 999.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA GeForce RTX 4080":      {"price": 899.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA GeForce RTX 4070 Ti Super": {"price": 799.99, "brand": "NVIDIA", "category": "GPU", "store": "B&H Photo"},
    "NVIDIA GeForce RTX 4070 Ti":   {"price": 749.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA GeForce RTX 4070 Super":{"price": 599.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA GeForce RTX 4070":      {"price": 549.99,  "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA GeForce RTX 4060 Ti":   {"price": 399.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA GeForce RTX 4060":      {"price": 299.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "AMD Radeon RX 7900 XTX":       {"price": 849.99,  "brand": "AMD",    "category": "GPU", "store": "Amazon"},
    "AMD Radeon RX 7900 XT":        {"price": 699.99,  "brand": "AMD",    "category": "GPU", "store": "Newegg"},
    "AMD Radeon RX 7800 XT":        {"price": 449.99,  "brand": "AMD",    "category": "GPU", "store": "Best Buy"},
    "AMD Radeon RX 7700 XT":        {"price": 349.99,  "brand": "AMD",    "category": "GPU", "store": "Amazon"},
    "AMD Radeon RX 7600":           {"price": 249.99,  "brand": "AMD",    "category": "GPU", "store": "Newegg"},
    "AMD Radeon RX 9070 XT":        {"price": 599.99,  "brand": "AMD",    "category": "GPU", "store": "Amazon"},
    "AMD Radeon RX 9070":           {"price": 499.99,  "brand": "AMD",    "category": "GPU", "store": "Newegg"},
    "AMD Radeon RX 6950 XT":        {"price": 499.99,  "brand": "AMD",    "category": "GPU", "store": "B&H Photo"},
    "AMD Radeon RX 6800 XT":        {"price": 399.99,  "brand": "AMD",    "category": "GPU", "store": "Amazon"},

    # Motherboards
    "ASUS ROG Crosshair X670E Hero":    {"price": 599.99, "brand": "ASUS",     "category": "Motherboard", "store": "Newegg"},
    "ASUS ROG Strix X670E-F Gaming":    {"price": 399.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "MSI MEG X670E ACE":                {"price": 549.99, "brand": "MSI",      "category": "Motherboard", "store": "B&H Photo"},
    "MSI MAG X670E Tomahawk":           {"price": 299.99, "brand": "MSI",      "category": "Motherboard", "store": "Newegg"},
    "Gigabyte X670E AORUS Master":      {"price": 499.99, "brand": "Gigabyte", "category": "Motherboard", "store": "Amazon"},
    "ASUS Prime X670-P":                {"price": 199.99, "brand": "ASUS",     "category": "Motherboard", "store": "Best Buy"},
    "ASUS ROG Strix B650E-F Gaming":    {"price": 299.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "MSI MAG B650 Tomahawk":            {"price": 199.99, "brand": "MSI",      "category": "Motherboard", "store": "Micro Center"},
    "Gigabyte B650 AORUS Elite AX":     {"price": 229.99, "brand": "Gigabyte", "category": "Motherboard", "store": "Newegg"},
    "ASUS ROG Maximus Z790 Hero":       {"price": 699.99, "brand": "ASUS",     "category": "Motherboard", "store": "B&H Photo"},
    "ASUS ROG Strix Z790-E Gaming":     {"price": 449.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "MSI MEG Z790 ACE":                 {"price": 599.99, "brand": "MSI",      "category": "Motherboard", "store": "Newegg"},
    "MSI MAG Z790 Tomahawk":            {"price": 249.99, "brand": "MSI",      "category": "Motherboard", "store": "Micro Center"},
    "Gigabyte Z790 AORUS Master":       {"price": 499.99, "brand": "Gigabyte", "category": "Motherboard", "store": "Amazon"},
    "ASUS Prime Z790-P":                {"price": 189.99, "brand": "ASUS",     "category": "Motherboard", "store": "Best Buy"},
    "ASUS ROG Strix B550-F Gaming":     {"price": 179.99, "brand": "ASUS",     "category": "Motherboard", "store": "Best Buy"},
    "MSI MAG B550 Tomahawk":            {"price": 149.99, "brand": "MSI",      "category": "Motherboard", "store": "Newegg"},
    "Gigabyte B550 AORUS Pro":          {"price": 159.99, "brand": "Gigabyte", "category": "Motherboard", "store": "Amazon"},
    "ASUS Prime B760-PLUS":             {"price": 149.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "MSI PRO B760M-A":                  {"price": 119.99, "brand": "MSI",      "category": "Motherboard", "store": "Micro Center"},

    # RAM
    "Corsair Vengeance DDR5-6000 32GB":     {"price": 109.99, "brand": "Corsair",  "category": "RAM", "store": "Amazon"},
    "Corsair Vengeance DDR5-6000 64GB":     {"price": 199.99, "brand": "Corsair",  "category": "RAM", "store": "Newegg"},
    "G.Skill Trident Z5 DDR5-6400 32GB":    {"price": 129.99, "brand": "G.Skill",  "category": "RAM", "store": "B&H Photo"},
    "G.Skill Trident Z5 DDR5-6400 64GB":    {"price": 239.99, "brand": "G.Skill",  "category": "RAM", "store": "Amazon"},
    "Kingston Fury Beast DDR5-5200 32GB":   {"price": 99.99,  "brand": "Kingston", "category": "RAM", "store": "Newegg"},
    "Kingston Fury Beast DDR5-5200 16GB":   {"price": 59.99,  "brand": "Kingston", "category": "RAM", "store": "Amazon"},
    "Corsair Vengeance DDR4-3200 32GB":     {"price": 74.99,  "brand": "Corsair",  "category": "RAM", "store": "Amazon"},
    "Corsair Vengeance DDR4-3200 16GB":     {"price": 44.99,  "brand": "Corsair",  "category": "RAM", "store": "Newegg"},
    "G.Skill Ripjaws V DDR4-3600 32GB":     {"price": 79.99,  "brand": "G.Skill",  "category": "RAM", "store": "B&H Photo"},
    "G.Skill Ripjaws V DDR4-3600 16GB":     {"price": 49.99,  "brand": "G.Skill",  "category": "RAM", "store": "Amazon"},
    "Kingston Fury Beast DDR4-3200 32GB":   {"price": 69.99,  "brand": "Kingston", "category": "RAM", "store": "Newegg"},
    "Crucial Pro DDR5-5600 32GB":           {"price": 89.99,  "brand": "Crucial",  "category": "RAM", "store": "Best Buy"},
    "Teamgroup T-Force DDR5-6000 32GB":     {"price": 94.99,  "brand": "Teamgroup","category": "RAM", "store": "Newegg"},

    # Storage
    "Samsung 990 Pro 2TB NVMe":             {"price": 169.99, "brand": "Samsung",  "category": "Storage", "store": "Amazon"},
    "Samsung 990 Pro 1TB NVMe":             {"price": 99.99,  "brand": "Samsung",  "category": "Storage", "store": "Best Buy"},
    "Samsung 980 Pro 2TB NVMe":             {"price": 149.99, "brand": "Samsung",  "category": "Storage", "store": "Newegg"},
    "WD Black SN850X 2TB NVMe":             {"price": 159.99, "brand": "WD",       "category": "Storage", "store": "Newegg"},
    "WD Black SN850X 1TB NVMe":             {"price": 99.99,  "brand": "WD",       "category": "Storage", "store": "B&H Photo"},
    "Seagate FireCuda 530 2TB NVMe":        {"price": 179.99, "brand": "Seagate",  "category": "Storage", "store": "Amazon"},
    "Crucial P5 Plus 2TB NVMe":             {"price": 129.99, "brand": "Crucial",  "category": "Storage", "store": "Best Buy"},
    "Crucial P5 Plus 1TB NVMe":             {"price": 74.99,  "brand": "Crucial",  "category": "Storage", "store": "Newegg"},
    "Samsung 870 EVO 2TB SATA SSD":         {"price": 149.99, "brand": "Samsung",  "category": "Storage", "store": "Amazon"},
    "Crucial MX500 1TB SATA SSD":           {"price": 64.99,  "brand": "Crucial",  "category": "Storage", "store": "Amazon"},
    "WD Blue 4TB HDD":                      {"price": 79.99,  "brand": "WD",       "category": "Storage", "store": "Newegg"},
    "Seagate Barracuda 4TB HDD":            {"price": 74.99,  "brand": "Seagate",  "category": "Storage", "store": "Best Buy"},

    # PSUs
    "Corsair RM1000x 1000W 80+ Gold":           {"price": 179.99, "brand": "Corsair",     "category": "PSU", "store": "Amazon"},
    "Corsair RM850x 850W 80+ Gold":             {"price": 149.99, "brand": "Corsair",     "category": "PSU", "store": "Newegg"},
    "Corsair RM750x 750W 80+ Gold":             {"price": 124.99, "brand": "Corsair",     "category": "PSU", "store": "Best Buy"},
    "Corsair RM650x 650W 80+ Gold":             {"price": 109.99, "brand": "Corsair",     "category": "PSU", "store": "Amazon"},
    "Seasonic Focus GX-1000 1000W 80+ Gold":    {"price": 189.99, "brand": "Seasonic",    "category": "PSU", "store": "Newegg"},
    "Seasonic Focus GX-850 850W 80+ Gold":      {"price": 154.99, "brand": "Seasonic",    "category": "PSU", "store": "B&H Photo"},
    "Seasonic Focus GX-750 750W 80+ Gold":      {"price": 129.99, "brand": "Seasonic",    "category": "PSU", "store": "Amazon"},
    "be quiet! Dark Power 13 1000W 80+ Titanium": {"price": 279.99, "brand": "be quiet!", "category": "PSU", "store": "Newegg"},
    "EVGA SuperNOVA 1000 G6 1000W 80+ Gold":    {"price": 169.99, "brand": "EVGA",        "category": "PSU", "store": "Newegg"},
    "Corsair HX1200 1200W 80+ Platinum":        {"price": 229.99, "brand": "Corsair",     "category": "PSU", "store": "Amazon"},
    "Corsair AX1600i 1600W 80+ Titanium":       {"price": 499.99, "brand": "Corsair",     "category": "PSU", "store": "Newegg"},

    # Cases
    "Lian Li PC-O11 Dynamic EVO":      {"price": 169.99, "brand": "Lian Li",      "category": "Case", "store": "Amazon"},
    "Lian Li PC-O11 Dynamic":          {"price": 139.99, "brand": "Lian Li",      "category": "Case", "store": "Newegg"},
    "Fractal Design Torrent":          {"price": 189.99, "brand": "Fractal",      "category": "Case", "store": "B&H Photo"},
    "Fractal Design Define 7":         {"price": 179.99, "brand": "Fractal",      "category": "Case", "store": "Newegg"},
    "Corsair 5000D Airflow":           {"price": 174.99, "brand": "Corsair",      "category": "Case", "store": "Best Buy"},
    "Corsair 4000D Airflow":           {"price": 94.99,  "brand": "Corsair",      "category": "Case", "store": "Amazon"},
    "NZXT H7 Flow":                    {"price": 149.99, "brand": "NZXT",         "category": "Case", "store": "B&H Photo"},
    "NZXT H510":                       {"price": 79.99,  "brand": "NZXT",         "category": "Case", "store": "Newegg"},
    "be quiet! Dark Base Pro 901":     {"price": 269.99, "brand": "be quiet!",    "category": "Case", "store": "Newegg"},
    "Cooler Master HAF 700 EVO":       {"price": 249.99, "brand": "Cooler Master","category": "Case", "store": "Amazon"},
    "Phanteks Enthoo Pro II":          {"price": 229.99, "brand": "Phanteks",     "category": "Case", "store": "B&H Photo"},

    # Coolers
    "Noctua NH-D15":                        {"price": 99.99,  "brand": "Noctua",        "category": "Cooler", "store": "Amazon"},
    "Noctua NH-U12S":                       {"price": 74.99,  "brand": "Noctua",        "category": "Cooler", "store": "Newegg"},
    "be quiet! Dark Rock Pro 4":            {"price": 89.99,  "brand": "be quiet!",     "category": "Cooler", "store": "Amazon"},
    "DeepCool AK620":                       {"price": 59.99,  "brand": "DeepCool",      "category": "Cooler", "store": "Newegg"},
    "Cooler Master Hyper 212":              {"price": 39.99,  "brand": "Cooler Master", "category": "Cooler", "store": "Best Buy"},
    "Corsair iCUE H150i Elite":             {"price": 199.99, "brand": "Corsair",       "category": "Cooler", "store": "Amazon"},
    "Corsair iCUE H100i Elite":             {"price": 149.99, "brand": "Corsair",       "category": "Cooler", "store": "Best Buy"},
    "NZXT Kraken X73":                      {"price": 179.99, "brand": "NZXT",          "category": "Cooler", "store": "Amazon"},
    "NZXT Kraken X53":                      {"price": 129.99, "brand": "NZXT",          "category": "Cooler", "store": "Newegg"},
    "Thermalright Peerless Assassin 120":   {"price": 44.99,  "brand": "Thermalright",  "category": "Cooler", "store": "Newegg"},
    "DeepCool LT720":                       {"price": 149.99, "brand": "DeepCool",      "category": "Cooler", "store": "Amazon"},
}

# ─── GPU sanity floors ────────────────────────────────────────────────────────
# Token → minimum price. Token matched via substring against model name (lowercase).

_GPU_PRICE_FLOOR: Dict[str, float] = {
    "5090": 1800.0,
    "5080": 1000.0,
    "5070 ti": 800.0,
    "5070": 600.0,
    "5060 ti": 400.0,
    "4090": 1500.0,
    "4080 super": 950.0,
    "4080": 850.0,
    "4070 ti super": 750.0,
    "4070 ti": 700.0,
    "4070 super": 550.0,
    "4070": 500.0,
    "4060 ti": 350.0,
    "7900 xtx": 800.0,
    "7900 xt": 650.0,
    "9070 xt": 550.0,
}

# ─── Category fallback prices ─────────────────────────────────────────────────

_CATEGORY_FALLBACK: Dict[str, float] = {
    "CPU":         250.0,
    "GPU":        2000.0,   # High default: most missing GPUs are high-end
    "Motherboard": 200.0,
    "RAM":         120.0,
    "Storage":     150.0,
    "PSU":         120.0,
    "Case":        130.0,
    "Cooler":       80.0,
    "Monitor":     300.0,
}

# ─── Store URL map ────────────────────────────────────────────────────────────

_STORE_URL_MAP: Dict[str, str] = {
    "Amazon":       "https://www.amazon.com/s?k={}",
    "Newegg":       "https://www.newegg.com/p/pl?d={}",
    "Best Buy":     "https://www.bestbuy.com/site/searchpage.jsp?st={}",
    "B&H Photo":    "https://www.bhphotovideo.com/c/search?q={}",
    "Micro Center": "https://www.microcenter.com/search/search_results.aspx?Ntt={}",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_url(model: str, store: str) -> str:
    template = _STORE_URL_MAP.get(store, "https://www.google.com/search?q={}")
    return template.format(model.replace(" ", "+"))


def _add_price_jitter(base_price: float, pct: float = 0.03) -> float:
    jitter = base_price * pct
    return round(random.uniform(base_price - jitter, base_price + jitter), 2)


def _apply_gpu_floor(model: str, price: float) -> float:
    """
    Enforce minimum price for known GPU tiers.
    Multi-word tokens (e.g. '5070 ti') are checked before single-word ones
    so that '5070 ti' is not matched by the shorter '5070' rule.
    """
    model_lower = model.lower()
    # Sort by length descending so multi-word tokens match first
    for token in sorted(_GPU_PRICE_FLOOR, key=len, reverse=True):
        if token in model_lower:
            return max(price, _GPU_PRICE_FLOOR[token])
    return price


def _fallback_price_value(category: str) -> float:
    return _CATEGORY_FALLBACK.get(category, 50.0)


def _num_tokens(s: str) -> set:
    """Extract 3+-digit numeric model tokens, e.g. '4090', '5090', '850x'."""
    return set(re.findall(r'\d{3,}[a-z]*', s.lower()))


# ─── PricingService ───────────────────────────────────────────────────────────

class PricingService:
    """
    Guaranteed pricing — never raises, never returns None, never returns 0.

    Resolution order for every component:
      1. Master Catalogue (if loaded — exact or normalised match)
      2. _PRICE_DB exact key match
      3. _PRICE_DB partial match (numeric model token overlap + word overlap)
      4. _PRICE_DB numeric-only match (handles short names like "RTX 5090 Ti")
      5. Category fallback floor (always succeeds)

    GPU sanity floor enforced at every stage.
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def get_price(self, model: str, category: str) -> PricedPart:
        """Always returns a PricedPart with price_usd > 0."""

        # Stage 1: Master Catalogue
        try:
            from backend.data.catalogue import master_catalogue
            if master_catalogue.is_loaded():
                comp = master_catalogue.find_by_name(model, category or None)
                if comp and comp.price_usd > 0:
                    price = comp.price_usd
                    if category == "GPU":
                        price = _apply_gpu_floor(comp.full_name, price)
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
            logger.debug("Catalogue lookup failed for '%s': %s", model, exc)

        # Stage 2: Exact DB key
        data = _PRICE_DB.get(model)
        if data:
            return self._build_priced_part(model, data, category)

        # Stage 3 + 4: Partial DB match
        match = self._partial_match(model, category)
        if match:
            return match

        # Stage 5: Hard fallback — always succeeds
        return self._fallback_priced_part(model, category)

    def get_all_by_category(self, category: str) -> List[PricedPart]:
        results: List[PricedPart] = []
        try:
            from backend.data.catalogue import master_catalogue
            if master_catalogue.is_loaded():
                for comp in master_catalogue.get_by_category(category):
                    if comp.price_usd > 0:
                        store = _PRICE_DB.get(comp.full_name, {}).get("store", "Newegg")
                        results.append(PricedPart(
                            category=comp.category,
                            brand=comp.brand,
                            model=comp.full_name,
                            price_usd=_add_price_jitter(comp.price_usd),
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
        for db_model, db_data in _PRICE_DB.items():
            if db_data["category"] == category:
                results.append(self._build_priced_part(db_model, db_data, category))
        return results

    def get_base_price(self, model: str) -> Optional[float]:
        data = _PRICE_DB.get(model)
        return data["price"] if data else None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _partial_match(self, model: str, category: str) -> Optional[PricedPart]:
        """
        Try to find a DB match based on numeric token overlap.
        Handles short names like "RTX 5090 Ti" where word-based overlap fails.
        """
        query_nums = _num_tokens(model)

        # Words longer than 3 chars that are not purely numeric
        q_words = {
            w.lower() for w in model.split()
            if len(w) > 3 and not w.isdigit() and not w.isnumeric()
        }

        for db_model, db_data in _PRICE_DB.items():
            if db_data["category"] != category:
                continue

            cand_nums = _num_tokens(db_model)

            # Numeric tokens from query must all appear in candidate
            if query_nums and not query_nums.issubset(cand_nums):
                continue

            c_words = {
                w.lower() for w in db_model.split()
                if len(w) > 3 and not w.isdigit() and not w.isnumeric()
            }

            # Case A: word-level overlap
            if q_words and c_words and (q_words & c_words):
                return self._build_priced_part(db_model, db_data, category)

            # Case B: no long words on either side (e.g. "RTX 5090 Ti" vs "NVIDIA RTX 5090")
            # — match on equal numeric tokens alone
            if query_nums and query_nums == cand_nums:
                return self._build_priced_part(db_model, db_data, category)

        return None

    def _build_priced_part(
        self, model: str, data: Dict[str, Any], category: str = ""
    ) -> PricedPart:
        price = data["price"]
        effective_category = data.get("category", category)
        if effective_category == "GPU":
            price = _apply_gpu_floor(model, price)
        return PricedPart(
            category=effective_category,
            brand=data["brand"],
            model=model,
            price_usd=_add_price_jitter(price),
            currency="USD",
            store=data["store"],
            availability="In Stock",
            url=_build_url(model, data["store"]),
            last_updated=datetime.now(timezone.utc),
            source="simulated",
        )

    def _fallback_priced_part(self, model: str, category: str) -> PricedPart:
        """Guaranteed last-resort. Applies GPU floor so 5090 never gets <$1800."""
        base = _fallback_price_value(category)
        if category == "GPU":
            base = _apply_gpu_floor(model, base)
        brand = model.split()[0] if model and model.split() else "Unknown"
        return PricedPart(
            category=category,
            brand=brand,
            model=model,
            price_usd=_add_price_jitter(base),
            currency="USD",
            store="Estimated",
            availability="Check Retailer",
            url=_build_url(model, "Amazon"),
            last_updated=datetime.now(timezone.utc),
            source="fallback",
        )


# ─── Singleton ────────────────────────────────────────────────────────────────

pricing_service = PricingService()