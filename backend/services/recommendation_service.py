"""
PCForge AI — Recommendation Service
Intelligent component selection based on build tier, usage, compatibility, and budget.
Returns primary recommendations + 2 alternatives per category, with reasoning.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.models.schemas import (
    AlternativeOption,
    BuildTier,
    RecommendedPart,
    RecommendationResult,
    UsageType,
)

# Load rules once at module level
_RULES_PATH = Path(__file__).parent.parent / "data" / "compatibility_rules.json"
with open(_RULES_PATH) as _f:
    _COMPAT_RULES: Dict[str, Any] = json.load(_f)

logger = logging.getLogger(__name__)

# ─── Component Catalogue ──────────────────────────────────────────────────────
# Each entry: (model, brand, socket, ram_type, form_factor, price, tier, usage_tags[])

_CPU_CATALOGUE = [
    # (model, brand, socket, price, tier, uses)
    # Budget
    ("AMD Ryzen 5 5600",       "AMD",   "AM4",     99.99,  "budget",      ["gaming", "mixed", "office"]),
    ("AMD Ryzen 5 5600X",      "AMD",   "AM4",     129.99, "budget",      ["gaming", "mixed"]),
    ("Intel Core i3-13100F",   "Intel", "LGA1700", 89.99,  "budget",      ["office", "mixed"]),
    ("Intel Core i3-14100F",   "Intel", "LGA1700", 99.99,  "budget",      ["office", "mixed"]),
    ("Intel Core i5-12400F",   "Intel", "LGA1700", 129.99, "budget",      ["gaming", "mixed"]),
    ("Intel Core i5-13400F",   "Intel", "LGA1700", 159.99, "budget",      ["gaming", "mixed"]),
    ("Intel Core i5-14400F",   "Intel", "LGA1700", 159.99, "budget",      ["gaming", "mixed"]),
    ("AMD Ryzen 5 7600",       "AMD",   "AM5",     149.99, "budget",      ["gaming", "mixed"]),
    ("AMD Ryzen 5 9600",       "AMD",   "AM5",     199.99, "budget",      ["gaming", "mixed"]),
    # Mid-range
    ("AMD Ryzen 5 7600X",      "AMD",   "AM5",     199.99, "mid-range",   ["gaming", "mixed"]),
    ("AMD Ryzen 5 9600X",      "AMD",   "AM5",     249.99, "mid-range",   ["gaming", "mixed"]),
    ("Intel Core i5-12600K",   "Intel", "LGA1700", 179.99, "mid-range",   ["gaming", "mixed"]),
    ("Intel Core i5-13600K",   "Intel", "LGA1700", 219.99, "mid-range",   ["gaming", "streaming", "mixed"]),
    ("Intel Core i5-14600K",   "Intel", "LGA1700", 249.99, "mid-range",   ["gaming", "streaming", "mixed"]),
    ("AMD Ryzen 7 7700",       "AMD",   "AM5",     199.99, "mid-range",   ["gaming", "streaming", "editing"]),
    ("AMD Ryzen 7 7700X",      "AMD",   "AM5",     249.99, "mid-range",   ["gaming", "streaming", "editing"]),
    ("AMD Ryzen 7 7800X3D",    "AMD",   "AM5",     399.99, "mid-range",   ["gaming"]),
    ("AMD Ryzen 7 5800X3D",    "AMD",   "AM4",     229.99, "mid-range",   ["gaming"]),
    # High-end
    ("AMD Ryzen 7 9700X",      "AMD",   "AM5",     329.99, "high-end",    ["gaming", "streaming", "editing"]),
    ("Intel Core i7-13700K",   "Intel", "LGA1700", 329.99, "high-end",    ["gaming", "streaming", "editing", "workstation"]),
    ("Intel Core i7-14700K",   "Intel", "LGA1700", 389.99, "high-end",    ["gaming", "streaming", "editing", "workstation"]),
    ("AMD Ryzen 9 7900X",      "AMD",   "AM5",     349.99, "high-end",    ["editing", "workstation", "streaming"]),
    ("AMD Ryzen 9 9900X",      "AMD",   "AM5",     449.99, "high-end",    ["editing", "workstation", "streaming", "gaming"]),
    # Enthusiast
    ("Intel Core i9-13900K",   "Intel", "LGA1700", 469.99, "enthusiast",  ["workstation", "editing", "streaming"]),
    ("Intel Core i9-14900K",   "Intel", "LGA1700", 569.99, "enthusiast",  ["workstation", "editing", "streaming"]),
    ("AMD Ryzen 9 7950X",      "AMD",   "AM5",     549.99, "enthusiast",  ["workstation", "editing", "streaming"]),
    ("AMD Ryzen 9 9950X",      "AMD",   "AM5",     649.99, "enthusiast",  ["workstation", "editing", "streaming", "gaming"]),
    ("AMD Ryzen 9 7950X3D",    "AMD",   "AM5",     699.99, "enthusiast",  ["workstation", "gaming"]),
]

_GPU_CATALOGUE = [
    # (model, brand, vram_gb, price, tier, uses)
    # Budget
    ("NVIDIA GeForce RTX 4060",      "NVIDIA", 8,  299.99, "budget",    ["gaming", "mixed", "streaming"]),
    ("AMD Radeon RX 7600",           "AMD",    8,  249.99, "budget",    ["gaming", "mixed"]),
    ("NVIDIA GeForce RTX 3060",      "NVIDIA", 12, 199.99, "budget",    ["gaming", "mixed"]),
    # Mid-range
    ("NVIDIA GeForce RTX 4060 Ti",   "NVIDIA", 8,  399.99, "mid-range", ["gaming", "streaming", "mixed"]),
    ("NVIDIA GeForce RTX 4070",      "NVIDIA", 12, 549.99, "mid-range", ["gaming", "streaming", "editing"]),
    ("AMD Radeon RX 7700 XT",        "AMD",    12, 349.99, "mid-range", ["gaming", "mixed"]),
    ("AMD Radeon RX 7800 XT",        "AMD",    16, 449.99, "mid-range", ["gaming", "streaming"]),
    ("NVIDIA GeForce RTX 5060 Ti",   "NVIDIA", 16, 429.99, "mid-range", ["gaming", "streaming"]),
    ("NVIDIA GeForce RTX 5070",      "NVIDIA", 12, 549.99, "mid-range", ["gaming", "streaming", "editing"]),
    # High-end
    ("NVIDIA GeForce RTX 4070 Super","NVIDIA", 12, 599.99, "high-end",  ["gaming", "streaming", "editing"]),
    ("NVIDIA GeForce RTX 4070 Ti",   "NVIDIA", 12, 749.99, "high-end",  ["gaming", "editing", "workstation"]),
    ("AMD Radeon RX 7900 GRE",       "AMD",    16, 499.99, "high-end",  ["gaming", "editing"]),
    ("AMD Radeon RX 7900 XT",        "AMD",    20, 699.99, "high-end",  ["gaming", "editing", "workstation"]),
    ("NVIDIA GeForce RTX 5070 Ti",   "NVIDIA", 16, 749.99, "high-end",  ["gaming", "editing", "workstation"]),
    ("AMD Radeon RX 9070 XT",        "AMD",    16, 599.99, "high-end",  ["gaming", "editing"]),
    # Enthusiast
    ("NVIDIA GeForce RTX 4080 Super","NVIDIA", 16, 999.99, "enthusiast", ["gaming", "editing", "workstation"]),
    ("AMD Radeon RX 7900 XTX",       "AMD",    24, 849.99, "enthusiast", ["gaming", "editing", "workstation"]),
    ("NVIDIA GeForce RTX 4090",      "NVIDIA", 24, 1599.99,"enthusiast", ["gaming", "editing", "workstation"]),
    ("NVIDIA GeForce RTX 5080",      "NVIDIA", 16, 999.99, "enthusiast", ["gaming", "editing", "workstation"]),
    ("NVIDIA GeForce RTX 5090",      "NVIDIA", 32, 1999.99,"enthusiast", ["gaming", "editing", "workstation"]),
]

_MB_CATALOGUE = [
    # (model, brand, socket, ram_type, form_factor, price, tier)
    ("Gigabyte B760M DS3H",              "Gigabyte", "LGA1700", "DDR4", "Micro-ATX", 99.99,  "budget"),
    ("MSI PRO B760M-A",                  "MSI",      "LGA1700", "DDR4", "Micro-ATX", 119.99, "budget"),
    ("ASUS Prime B760-PLUS",             "ASUS",     "LGA1700", "DDR5", "ATX",       149.99, "budget"),
    ("ASRock B550M Pro4",                "ASRock",   "AM4",     "DDR4", "Micro-ATX", 109.99, "budget"),
    ("MSI MAG B550 Tomahawk",            "MSI",      "AM4",     "DDR4", "ATX",       149.99, "budget"),
    ("ASUS ROG Strix B550-F Gaming",     "ASUS",     "AM4",     "DDR4", "ATX",       179.99, "mid-range"),
    ("Gigabyte B550 AORUS Pro",          "Gigabyte", "AM4",     "DDR4", "ATX",       159.99, "mid-range"),
    ("ASRock B650M Pro RS",              "ASRock",   "AM5",     "DDR5", "Micro-ATX", 139.99, "budget"),
    ("Gigabyte B650 AORUS Elite AX",     "Gigabyte", "AM5",     "DDR5", "ATX",       229.99, "mid-range"),
    ("MSI MAG B650 Tomahawk",            "MSI",      "AM5",     "DDR5", "ATX",       199.99, "mid-range"),
    ("ASUS Prime B650-PLUS",             "ASUS",     "AM5",     "DDR5", "ATX",       154.99, "budget"),
    ("MSI MAG Z690 Tomahawk",            "MSI",      "LGA1700", "DDR5", "ATX",       199.99, "mid-range"),
    ("Gigabyte Z690 AORUS Pro",          "Gigabyte", "LGA1700", "DDR5", "ATX",       229.99, "mid-range"),
    ("ASUS ROG Strix Z690-E Gaming",     "ASUS",     "LGA1700", "DDR5", "ATX",       349.99, "high-end"),
    ("MSI MAG Z790 Tomahawk",            "MSI",      "LGA1700", "DDR5", "ATX",       249.99, "mid-range"),
    ("ASUS Prime Z790-P",                "ASUS",     "LGA1700", "DDR5", "ATX",       189.99, "mid-range"),
    ("Gigabyte Z790 AORUS Master",       "Gigabyte", "LGA1700", "DDR5", "E-ATX",     499.99, "high-end"),
    ("ASUS ROG Strix Z790-E Gaming",     "ASUS",     "LGA1700", "DDR5", "ATX",       449.99, "high-end"),
    ("MSI MEG Z790 ACE",                 "MSI",      "LGA1700", "DDR5", "E-ATX",     599.99, "enthusiast"),
    ("MSI MAG X570 Tomahawk",            "MSI",      "AM4",     "DDR4", "ATX",       199.99, "mid-range"),
    ("Gigabyte X570 AORUS Master",       "Gigabyte", "AM4",     "DDR4", "ATX",       279.99, "high-end"),
    ("ASUS ROG Strix X570-E Gaming",     "ASUS",     "AM4",     "DDR4", "ATX",       259.99, "high-end"),
    ("MSI MAG X670E Tomahawk",           "MSI",      "AM5",     "DDR5", "ATX",       299.99, "high-end"),
    ("ASUS ROG Strix X670E-F Gaming",    "ASUS",     "AM5",     "DDR5", "ATX",       399.99, "high-end"),
    ("Gigabyte X670E AORUS Master",      "Gigabyte", "AM5",     "DDR5", "E-ATX",     499.99, "enthusiast"),
    ("ASUS ROG Crosshair X670E Hero",    "ASUS",     "AM5",     "DDR5", "ATX",       599.99, "enthusiast"),
    ("MSI MEG X670E ACE",                "MSI",      "AM5",     "DDR5", "E-ATX",     549.99, "enthusiast"),
]

_RAM_CATALOGUE = [
    # (model, brand, type, size_gb, speed_mhz, price, tier)
    ("Kingston Fury Beast DDR4-3200 16GB",  "Kingston", "DDR4", 16, 3200, 39.99,  "budget"),
    ("Corsair Vengeance DDR4-3200 16GB",    "Corsair",  "DDR4", 16, 3200, 44.99,  "budget"),
    ("G.Skill Ripjaws V DDR4-3600 16GB",    "G.Skill",  "DDR4", 16, 3600, 49.99,  "budget"),
    ("Kingston Fury Beast DDR4-3200 32GB",  "Kingston", "DDR4", 32, 3200, 69.99,  "mid-range"),
    ("Corsair Vengeance DDR4-3200 32GB",    "Corsair",  "DDR4", 32, 3200, 74.99,  "mid-range"),
    ("G.Skill Ripjaws V DDR4-3600 32GB",    "G.Skill",  "DDR4", 32, 3600, 79.99,  "mid-range"),
    ("Kingston Fury Beast DDR5-5200 16GB",  "Kingston", "DDR5", 16, 5200, 59.99,  "budget"),
    ("Crucial Pro DDR5-5600 32GB",          "Crucial",  "DDR5", 32, 5600, 89.99,  "mid-range"),
    ("Kingston Fury Beast DDR5-5200 32GB",  "Kingston", "DDR5", 32, 5200, 99.99,  "mid-range"),
    ("Corsair Vengeance DDR5-6000 32GB",    "Corsair",  "DDR5", 32, 6000, 109.99, "mid-range"),
    ("Teamgroup T-Force DDR5-6000 32GB",    "Teamgroup","DDR5", 32, 6000, 94.99,  "mid-range"),
    ("G.Skill Trident Z5 DDR5-6400 32GB",   "G.Skill",  "DDR5", 32, 6400, 129.99, "high-end"),
    ("Corsair Vengeance DDR5-6000 64GB",    "Corsair",  "DDR5", 64, 6000, 199.99, "high-end"),
    ("G.Skill Trident Z5 DDR5-6400 64GB",   "G.Skill",  "DDR5", 64, 6400, 239.99, "enthusiast"),
]

_STORAGE_CATALOGUE = [
    # (model, brand, type, capacity_gb, price, tier)
    ("Crucial MX500 1TB SATA SSD",    "Crucial",  "SATA SSD", 1024, 64.99,  "budget"),
    ("Samsung 870 EVO 1TB SATA SSD",  "Samsung",  "SATA SSD", 1024, 79.99,  "budget"),
    ("Crucial P5 Plus 1TB NVMe",      "Crucial",  "NVMe",     1024, 74.99,  "budget"),
    ("Samsung 990 EVO 1TB NVMe",      "Samsung",  "NVMe",     1024, 84.99,  "budget"),
    ("WD Black SN850X 1TB NVMe",      "WD",       "NVMe",     1024, 99.99,  "mid-range"),
    ("Samsung 980 Pro 1TB NVMe",      "Samsung",  "NVMe",     1024, 89.99,  "mid-range"),
    ("Crucial MX500 2TB SATA SSD",    "Crucial",  "SATA SSD", 2048, 99.99,  "mid-range"),
    ("Seagate FireCuda 530 1TB NVMe", "Seagate",  "NVMe",     1024, 109.99, "mid-range"),
    ("Samsung 980 Pro 2TB NVMe",      "Samsung",  "NVMe",     2048, 149.99, "high-end"),
    ("WD Black SN850X 2TB NVMe",      "WD",       "NVMe",     2048, 159.99, "high-end"),
    ("Samsung 990 Pro 1TB NVMe",      "Samsung",  "NVMe",     1024, 99.99,  "mid-range"),
    ("Samsung 990 Pro 2TB NVMe",      "Samsung",  "NVMe",     2048, 169.99, "high-end"),
    ("Seagate FireCuda 530 2TB NVMe", "Seagate",  "NVMe",     2048, 179.99, "high-end"),
    ("WD Blue 4TB HDD",               "WD",       "HDD",      4096, 79.99,  "budget"),
    ("Seagate Barracuda 4TB HDD",     "Seagate",  "HDD",      4096, 74.99,  "budget"),
]

_PSU_CATALOGUE = [
    # (model, brand, wattage, rating, price, tier)
    ("be quiet! Pure Power 12M 750W 80+ Gold",         "be quiet!", 750,  "80+ Gold",     99.99,  "budget"),
    ("Cooler Master MWE Gold 650W",                     "Cooler Master", 650, "80+ Gold",  84.99,  "budget"),
    ("EVGA SuperNOVA 750 G6 750W 80+ Gold",             "EVGA",     750,  "80+ Gold",     119.99, "mid-range"),
    ("Corsair RM750x 750W 80+ Gold",                    "Corsair",  750,  "80+ Gold",     124.99, "mid-range"),
    ("Corsair RM650x 650W 80+ Gold",                    "Corsair",  650,  "80+ Gold",     109.99, "budget"),
    ("Seasonic Focus GX-750 750W 80+ Gold",             "Seasonic", 750,  "80+ Gold",     129.99, "mid-range"),
    ("EVGA SuperNOVA 850 G6 850W 80+ Gold",             "EVGA",     850,  "80+ Gold",     139.99, "high-end"),
    ("Corsair RM850x 850W 80+ Gold",                    "Corsair",  850,  "80+ Gold",     149.99, "high-end"),
    ("Seasonic Focus GX-850 850W 80+ Gold",             "Seasonic", 850,  "80+ Gold",     154.99, "high-end"),
    ("be quiet! Straight Power 11 850W 80+ Platinum",   "be quiet!", 850, "80+ Platinum", 159.99, "high-end"),
    ("EVGA SuperNOVA 1000 G6 1000W 80+ Gold",           "EVGA",     1000, "80+ Gold",     169.99, "enthusiast"),
    ("Corsair RM1000x 1000W 80+ Gold",                  "Corsair",  1000, "80+ Gold",     179.99, "enthusiast"),
    ("Seasonic Focus GX-1000 1000W 80+ Gold",           "Seasonic", 1000, "80+ Gold",     189.99, "enthusiast"),
    ("be quiet! Dark Power 13 1000W 80+ Titanium",      "be quiet!", 1000, "80+ Titanium",279.99, "enthusiast"),
    ("Corsair HX1200 1200W 80+ Platinum",               "Corsair",  1200, "80+ Platinum", 229.99, "enthusiast"),
]

_CASE_CATALOGUE = [
    # (model, brand, form_factors[], gpu_clearance, cooler_clearance, price, tier)
    ("Silverstone FARA R1",             "Silverstone",   ["ATX", "Micro-ATX", "Mini-ITX"], 340, 160, 69.99,  "budget"),
    ("NZXT H510",                       "NZXT",          ["ATX", "Micro-ATX", "Mini-ITX"], 381, 165, 79.99,  "budget"),
    ("Deepcool CH510",                  "Deepcool",      ["ATX", "Micro-ATX", "Mini-ITX"], 370, 165, 79.99,  "budget"),
    ("Cooler Master MasterBox TD500",   "Cooler Master", ["ATX", "Micro-ATX", "Mini-ITX"], 410, 165, 89.99,  "budget"),
    ("Corsair 4000D Airflow",           "Corsair",       ["ATX", "Micro-ATX", "Mini-ITX"], 360, 170, 94.99,  "mid-range"),
    ("Antec P120 Crystal",              "Antec",         ["ATX", "Micro-ATX", "Mini-ITX"], 400, 165, 119.99, "mid-range"),
    ("be quiet! Pure Base 500DX",       "be quiet!",     ["ATX", "Micro-ATX", "Mini-ITX"], 369, 190, 109.99, "mid-range"),
    ("Lian Li PC-O11 Dynamic",          "Lian Li",       ["ATX", "Micro-ATX", "Mini-ITX"], 420, 167, 139.99, "mid-range"),
    ("NZXT H510 Elite",                 "NZXT",          ["ATX", "Micro-ATX", "Mini-ITX"], 381, 165, 149.99, "mid-range"),
    ("NZXT H7 Flow",                    "NZXT",          ["ATX", "Micro-ATX", "Mini-ITX", "E-ATX"], 400, 185, 149.99, "mid-range"),
    ("Corsair 5000D Airflow",           "Corsair",       ["ATX", "Micro-ATX", "Mini-ITX"], 420, 170, 174.99, "high-end"),
    ("Fractal Design Define 7",         "Fractal",       ["ATX", "Micro-ATX", "Mini-ITX", "E-ATX"], 467, 185, 179.99, "high-end"),
    ("Fractal Design Torrent",          "Fractal",       ["ATX", "Micro-ATX", "Mini-ITX", "E-ATX"], 461, 185, 189.99, "high-end"),
    ("Thermaltake Core P6",             "Thermaltake",   ["ATX", "Micro-ATX", "Mini-ITX", "E-ATX"], 500, 210, 199.99, "high-end"),
    ("Lian Li PC-O11 Dynamic EVO",      "Lian Li",       ["ATX", "Micro-ATX", "Mini-ITX", "E-ATX"], 435, 167, 169.99, "high-end"),
    ("Phanteks Enthoo Pro II",          "Phanteks",      ["ATX", "Micro-ATX", "Mini-ITX", "E-ATX"], 503, 200, 229.99, "enthusiast"),
    ("be quiet! Dark Base Pro 901",     "be quiet!",     ["ATX", "Micro-ATX", "Mini-ITX", "E-ATX"], 490, 185, 269.99, "enthusiast"),
    ("Cooler Master HAF 700 EVO",       "Cooler Master", ["ATX", "Micro-ATX", "Mini-ITX", "E-ATX"], 490, 200, 249.99, "enthusiast"),
]

_COOLER_CATALOGUE = [
    # (model, brand, height_mm, tdp_support, is_aio, price, tier)
    ("ID-COOLING SE-224-XT",            "ID-COOLING",    154, 200, False, 29.99,  "budget"),
    ("ARCTIC Freezer 34 eSports",       "ARCTIC",        157, 200, False, 34.99,  "budget"),
    ("Cooler Master Hyper 212",         "Cooler Master", 159, 150, False, 39.99,  "budget"),
    ("DeepCool AG400",                  "DeepCool",      154, 220, False, 39.99,  "budget"),
    ("Thermalright Peerless Assassin 120","Thermalright", 155, 220, False, 44.99,  "budget"),
    ("be quiet! Shadow Rock 3",         "be quiet!",     160, 190, False, 49.99,  "mid-range"),
    ("DeepCool AK620",                  "DeepCool",      160, 260, False, 59.99,  "mid-range"),
    ("Noctua NH-U9S",                   "Noctua",        125, 160, False, 59.99,  "mid-range"),
    ("Noctua NH-U12S",                  "Noctua",        158, 220, False, 74.99,  "mid-range"),
    ("be quiet! Dark Rock 4",           "be quiet!",     159, 200, False, 74.99,  "mid-range"),
    ("Noctua NH-D15",                   "Noctua",        165, 250, False, 99.99,  "high-end"),
    ("be quiet! Dark Rock Pro 4",       "be quiet!",     162, 250, False, 89.99,  "high-end"),
    ("Thermaltake TH360 ARGB",          "Thermaltake",   27,  280, True,  119.99, "mid-range"),
    ("Cooler Master MasterLiquid ML360R","Cooler Master", 27,  300, True,  129.99, "high-end"),
    ("NZXT Kraken X53",                 "NZXT",          27,  300, True,  129.99, "high-end"),
    ("Corsair iCUE H100i Elite",        "Corsair",       27,  300, True,  149.99, "high-end"),
    ("DeepCool LT720",                  "DeepCool",      27,  300, True,  149.99, "high-end"),
    ("Lian Li Galahad 360",             "Lian Li",       27,  350, True,  159.99, "high-end"),
    ("NZXT Kraken X73",                 "NZXT",          27,  350, True,  179.99, "enthusiast"),
    ("Corsair iCUE H150i Elite",        "Corsair",       27,  350, True,  199.99, "enthusiast"),
]


# ─── Tier Inference ───────────────────────────────────────────────────────────

_TIER_BUDGET_MAP = {
    "budget":     (0, 800),
    "mid-range":  (801, 1800),
    "high-end":   (1801, 3500),
    "enthusiast": (3501, 999999),
}

_USAGE_TIER_MAP: Dict[str, BuildTier] = {
    "office":     "budget",
    "gaming":     "mid-range",
    "streaming":  "mid-range",
    "editing":    "high-end",
    "workstation":"enthusiast",
    "mixed":      "mid-range",
}


def _infer_tier(
    cpu: Optional[str],
    gpu: Optional[str],
    budget: Optional[float],
    usage: Optional[str],
) -> Tuple[BuildTier, str]:
    """
    Infer the build tier from available signals.
    Priority: budget > GPU > CPU > usage_type.
    """
    # Signal: budget
    if budget:
        for tier, (lo, hi) in _TIER_BUDGET_MAP.items():
            if lo <= budget <= hi:
                return tier, f"Inferred from budget ${budget:.0f}"

    # Signal: GPU
    if gpu:
        gpu_lower = gpu.lower()
        if any(x in gpu_lower for x in ["5090", "5080", "4090", "4080", "7900 xtx", "3090", "6950"]):
            return "enthusiast", f"Inferred from high-end GPU: {gpu}"
        if any(x in gpu_lower for x in ["5070 ti", "4070 ti", "4070 super", "3080", "7900 xt", "9070", "6800"]):
            return "high-end", f"Inferred from high-end GPU: {gpu}"
        if any(x in gpu_lower for x in ["5070", "5060 ti", "4070", "4060 ti", "3070", "7800", "6700"]):
            return "mid-range", f"Inferred from mid-tier GPU: {gpu}"

    # Signal: CPU
    if cpu:
        cpu_lower = cpu.lower()
        if any(x in cpu_lower for x in ["i9", "ryzen 9", "14900", "13900", "9950", "9900", "7950", "7900"]):
            return "enthusiast", f"Inferred from high-end CPU: {cpu}"
        if any(x in cpu_lower for x in ["i7", "ryzen 7", "14700", "13700", "9700", "7700"]):
            return "high-end", f"Inferred from high-tier CPU: {cpu}"
        if any(x in cpu_lower for x in ["i5", "ryzen 5", "14600", "13600", "9600", "7600"]):
            return "mid-range", f"Inferred from mid-tier CPU: {cpu}"

    # Signal: usage type
    if usage:
        tier = _USAGE_TIER_MAP.get(usage, "mid-range")
        return tier, f"Inferred from usage type: {usage}"

    return "mid-range", "Default tier (no strong signals available)"


def _within_budget(price: float, remaining_budget: Optional[float]) -> bool:
    if remaining_budget is None:
        return True
    return price <= remaining_budget


def _brand_match(brand: str, preferred_brand: Optional[str]) -> bool:
    if not preferred_brand:
        return True
    return preferred_brand.lower() in brand.lower()


# ─── Component Selectors ──────────────────────────────────────────────────────

def _select_motherboard(
    cpu_socket: str, ram_type: str, form_factor_needed: Optional[str],
    tier: str, budget: Optional[float], preferred_brand: Optional[str]
) -> Tuple[Optional[Dict], List[Dict]]:
    """Select best matching motherboard + 2 alternatives."""
    candidates = [
        m for m in _MB_CATALOGUE
        if m[2] == cpu_socket and m[3] == ram_type
    ]
    tier_order = ["budget", "mid-range", "high-end", "enthusiast"]
    tier_idx = tier_order.index(tier) if tier in tier_order else 1

    # Sort: prefer tier match, then price
    def score(m):
        m_tier_idx = tier_order.index(m[6]) if m[6] in tier_order else 1
        tier_distance = abs(m_tier_idx - tier_idx)
        brand_bonus = -10 if _brand_match(m[1], preferred_brand) else 0
        return (tier_distance, brand_bonus, m[5])

    candidates.sort(key=score)
    if not candidates:
        return None, []

    primary = candidates[0]
    alts = [c for c in candidates[1:] if c != primary][:2]
    return primary, alts


def _select_ram(
    ram_type: str, tier: str, budget: Optional[float],
    usage: Optional[str], preferred_brand: Optional[str]
) -> Tuple[Optional[Dict], List[Dict]]:
    """Select appropriate RAM kit."""
    # Determine target size by usage/tier
    size_map = {
        "budget": 16, "mid-range": 32, "high-end": 32, "enthusiast": 64
    }
    if usage in ("editing", "workstation"):
        size_map["mid-range"] = 32
        size_map["high-end"] = 64

    target_size = size_map.get(tier, 32)
    candidates = [r for r in _RAM_CATALOGUE if r[2] == ram_type]

    def score(r):
        size_diff = abs(r[3] - target_size)
        brand_bonus = -5 if _brand_match(r[1], preferred_brand) else 0
        return (size_diff, brand_bonus, r[5])

    candidates.sort(key=score)
    if not candidates:
        return None, []

    primary = candidates[0]
    alts = [c for c in candidates[1:] if c[3] == primary[3]][:2]
    return primary, alts


def _select_storage(
    tier: str, usage: Optional[str], preferred_brand: Optional[str]
) -> Tuple[Optional[Dict], List[Dict]]:
    """Select primary storage drive."""
    # NVMe for gaming/editing, SATA is fine for budget office
    preferred_type = "NVMe" if tier in ("mid-range", "high-end", "enthusiast") else "SATA SSD"
    if usage in ("gaming", "editing", "workstation"):
        preferred_type = "NVMe"

    # Capacity targets
    capacity_map = {"budget": 512, "mid-range": 1024, "high-end": 2048, "enthusiast": 2048}
    target_cap = capacity_map.get(tier, 1024)

    candidates = [
        s for s in _STORAGE_CATALOGUE
        if s[2] == preferred_type or (preferred_type == "NVMe" and "NVMe" in s[2])
    ]

    def score(s):
        cap_diff = abs(s[3] - target_cap)
        brand_bonus = -5 if _brand_match(s[1], preferred_brand) else 0
        return (cap_diff, brand_bonus, s[4])

    candidates.sort(key=score)
    if not candidates:
        candidates = _STORAGE_CATALOGUE[:]
        candidates.sort(key=lambda s: s[4])

    primary = candidates[0]
    alts = candidates[1:3]
    return primary, alts


def _calc_required_psu(cpu: Optional[str], gpu: Optional[str]) -> int:
    """Calculate minimum PSU wattage: (CPU_TDP + GPU_TDP + 100W_base) × 1.30 headroom."""
    cpu_tdp = _COMPAT_RULES.get("cpu_tdp_watts", {}).get(cpu, 125) if cpu else 125
    gpu_tdp = _COMPAT_RULES.get("gpu_tdp_watts", {}).get(gpu, 200) if gpu else 200
    base    = 100
    total   = cpu_tdp + gpu_tdp + base
    return int(total * 1.30)   # 30% headroom — never allow underpowered build


def _select_psu(
    cpu: Optional[str], gpu: Optional[str],
    tier: str, preferred_brand: Optional[str]
) -> Tuple[Optional[Dict], List[Dict]]:
    """Select PSU with enough headroom."""
    required = _calc_required_psu(cpu, gpu)
    candidates = [p for p in _PSU_CATALOGUE if p[2] >= required]

    def score(p):
        watt_excess = p[2] - required  # prefer minimal excess
        brand_bonus = -5 if _brand_match(p[1], preferred_brand) else 0
        return (watt_excess, brand_bonus, p[4])

    candidates.sort(key=score)
    if not candidates:
        # Fallback: highest available
        candidates = sorted(_PSU_CATALOGUE, key=lambda p: -p[2])

    primary = candidates[0]
    alts = candidates[1:3]
    return primary, alts


def _select_case(
    mb_form_factor: str, gpu: Optional[str],
    tier: str, preferred_brand: Optional[str]
) -> Tuple[Optional[Dict], List[Dict]]:
    """Select case supporting the motherboard form factor and GPU."""
    gpu_length = _COMPAT_RULES.get("gpu_length_mm", {}).get(gpu, 300) if gpu else 300

    candidates = [
        c for c in _CASE_CATALOGUE
        if mb_form_factor in c[2] and c[3] >= gpu_length
    ]
    tier_order = ["budget", "mid-range", "high-end", "enthusiast"]
    tier_idx = tier_order.index(tier) if tier in tier_order else 1

    def score(c):
        c_tier_idx = tier_order.index(c[6]) if c[6] in tier_order else 1
        brand_bonus = -5 if _brand_match(c[1], preferred_brand) else 0
        return (abs(c_tier_idx - tier_idx), brand_bonus, c[5])

    candidates.sort(key=score)
    if not candidates:
        candidates = sorted(_CASE_CATALOGUE, key=lambda c: c[5])

    primary = candidates[0]
    alts = candidates[1:3]
    return primary, alts


def _select_cooler(
    cpu: Optional[str], tier: str, case_clearance: Optional[int],
    preferred_brand: Optional[str]
) -> Tuple[Optional[Dict], List[Dict]]:
    """Select CPU cooler based on TDP requirements and clearance."""
    cpu_tdp = _COMPAT_RULES.get("cpu_tdp_watts", {}).get(cpu, 125) if cpu else 125
    clearance = case_clearance or 170

    # Prefer AIO for enthusiast/high-end, air for budget/mid
    prefer_aio = tier in ("high-end", "enthusiast") and cpu_tdp >= 150

    candidates = [
        c for c in _COOLER_CATALOGUE
        if c[3] >= cpu_tdp and (c[4] if prefer_aio else not c[4] or cpu_tdp > 200)
    ]
    # Filter by clearance (skip for AIOs)
    candidates = [c for c in candidates if c[4] or c[2] <= clearance]

    tier_order = ["budget", "mid-range", "high-end", "enthusiast"]
    tier_idx = tier_order.index(tier) if tier in tier_order else 1

    def score(c):
        c_tier_idx = tier_order.index(c[6]) if c[6] in tier_order else 1
        aio_bonus = -3 if (c[4] == prefer_aio) else 0
        brand_bonus = -2 if _brand_match(c[1], preferred_brand) else 0
        return (abs(c_tier_idx - tier_idx), aio_bonus, brand_bonus, c[5])

    candidates.sort(key=score)
    if not candidates:
        candidates = sorted(_COOLER_CATALOGUE, key=lambda c: c[5])

    primary = candidates[0]
    alts = candidates[1:3]
    return primary, alts


# ─── Main Recommendation Engine ───────────────────────────────────────────────

def run_recommendations(
    cpu: Optional[str] = None,
    gpu: Optional[str] = None,
    motherboard: Optional[str] = None,
    ram: Optional[Dict[str, Any]] = None,
    storage: Optional[List[Dict]] = None,
    psu: Optional[str] = None,
    case: Optional[str] = None,
    cooler: Optional[str] = None,
    budget_usd: Optional[float] = None,
    preferred_brand: Optional[str] = None,
    usage_type: Optional[str] = None,
) -> RecommendationResult:
    """
    Infer build tier and fill missing components with compatible recommendations.
    Returns primary picks + 2 alternatives per category with reasoning.
    """
    recommended_parts: List[RecommendedPart] = []
    alternatives: Dict[str, List[AlternativeOption]] = {}

    # ── Infer tier ─────────────────────────────────────────────────────────
    tier, tier_reasoning = _infer_tier(cpu, gpu, budget_usd, usage_type)

    # ── Determine RAM type needed ──────────────────────────────────────────
    # Derive from CPU / known socket
    ram_type = None
    if ram and isinstance(ram, dict):
        ram_type = ram.get("type")
    if not ram_type:
        # Infer from CPU — check Ryzen 9000 (AM5), 7000 (AM5), Intel 12/13/14 (DDR5), AM4 (DDR4)
        if cpu:
            cu = cpu.lower()
            if any(x in cu for x in ["9950", "9900", "9700", "9600",          # Ryzen 9000 → AM5
                                      "7950", "7900", "7800", "7700", "7600"]):  # Ryzen 7000 → AM5
                ram_type = "DDR5"
            elif any(x in cu for x in ["i9-14", "i7-14", "i5-14", "i3-14",
                                        "i9-13", "i7-13", "i5-13", "i3-13",
                                        "i9-12", "i7-12", "i5-12", "i3-12"]):
                ram_type = "DDR5"
            elif any(x in cu for x in ["5950", "5900", "5800", "5600",
                                        "3600", "3700", "3900"]):
                ram_type = "DDR4"
        if not ram_type:
            ram_type = "DDR5" if tier in ("mid-range", "high-end", "enthusiast") else "DDR4"

    # ── GPU recommendation (if missing) ────────────────────────────────────
    if not gpu:
        gpu_candidates = [
            g for g in _GPU_CATALOGUE
            if g[4] == tier
            and (not usage_type or usage_type in g[5])
        ]
        if not gpu_candidates:
            gpu_candidates = [g for g in _GPU_CATALOGUE if g[4] == tier]
        if not gpu_candidates:
            # Tier fallback: pick closest tier
            tier_order = ["budget", "mid-range", "high-end", "enthusiast"]
            t_idx = tier_order.index(tier) if tier in tier_order else 1
            gpu_candidates = sorted(
                _GPU_CATALOGUE, key=lambda g: abs(tier_order.index(g[4]) - t_idx)
            )

        best_gpu = gpu_candidates[0]
        recommended_parts.append(RecommendedPart(
            category="GPU",
            model=best_gpu[0],
            brand=best_gpu[1],
            reasoning=f"Best {tier} GPU ({best_gpu[2]}GB VRAM) for {usage_type or 'general'} use at ~${best_gpu[3]:.0f}",
            price_usd=best_gpu[3],
            compatibility_score=0.95,
        ))
        gpu_alts = [g for g in gpu_candidates[1:] if g[1] != best_gpu[1]][:1] + \
                   [g for g in gpu_candidates[1:] if g[1] == best_gpu[1]][:1]
        alternatives["GPU"] = [
            AlternativeOption(model=g[0], brand=g[1], price_usd=g[3],
                              notes=f"{g[2]}GB VRAM, {g[4]} tier")
            for g in gpu_alts[:2]
        ]
        gpu = best_gpu[0]

    # ── CPU recommendation (if missing) ───────────────────────────────────
    if not cpu:
        cpu_candidates = [
            c for c in _CPU_CATALOGUE
            if tier in (c[4], "any")
            and (not usage_type or usage_type in c[5])
        ]
        if not cpu_candidates:
            cpu_candidates = [c for c in _CPU_CATALOGUE if c[4] == tier]
        if not cpu_candidates:
            cpu_candidates = sorted(_CPU_CATALOGUE, key=lambda x: x[3])

        best_cpu = cpu_candidates[0]
        recommended_parts.append(RecommendedPart(
            category="CPU",
            model=best_cpu[0],
            brand=best_cpu[1],
            reasoning=f"Best {tier} CPU for {usage_type or 'general'} use at ~${best_cpu[3]:.0f}",
            price_usd=best_cpu[3],
            compatibility_score=0.95,
        ))
        cpu_alts = cpu_candidates[1:3]
        alternatives["CPU"] = [
            AlternativeOption(model=c[0], brand=c[1], price_usd=c[3], notes=f"{c[4]} option, {c[2]} socket")
            for c in cpu_alts
        ]
        # Use resolved CPU for downstream compatibility
        cpu = best_cpu[0]

    # ── Determine CPU socket for motherboard matching ──────────────────────
    cpu_socket = _COMPAT_RULES["cpu_socket_map"].get(cpu, "AM5")
    # Also update ram_type based on resolved socket
    if cpu_socket == "AM5":
        ram_type = "DDR5"
    elif cpu_socket in ("AM4",):
        ram_type = "DDR4"


    # ── Motherboard recommendation ─────────────────────────────────────────
    if not motherboard:
        primary_mb, alt_mbs = _select_motherboard(cpu_socket, ram_type, None, tier, budget_usd, preferred_brand)
        if primary_mb:
            recommended_parts.append(RecommendedPart(
                category="Motherboard",
                model=primary_mb[0],
                brand=primary_mb[1],
                reasoning=f"{primary_mb[6]} tier {primary_mb[2]} motherboard supporting {primary_mb[3]} RAM, {primary_mb[4]} form factor",
                price_usd=primary_mb[5],
                compatibility_score=0.98,
            ))
            alternatives["Motherboard"] = [
                AlternativeOption(model=m[0], brand=m[1], price_usd=m[5], notes=f"{m[4]} form factor, {m[3]} RAM")
                for m in alt_mbs
            ]
            motherboard = primary_mb[0]

    # ── RAM recommendation ─────────────────────────────────────────────────
    if not ram:
        primary_ram, alt_rams = _select_ram(ram_type, tier, budget_usd, usage_type, preferred_brand)
        if primary_ram:
            recommended_parts.append(RecommendedPart(
                category="RAM",
                model=primary_ram[0],
                brand=primary_ram[1],
                reasoning=f"{primary_ram[3]}GB {primary_ram[2]}-{primary_ram[4]}MHz — ideal for {usage_type or 'general'} use at {tier} tier",
                price_usd=primary_ram[5],
                compatibility_score=0.97,
            ))
            alternatives["RAM"] = [
                AlternativeOption(model=r[0], brand=r[1], price_usd=r[5], notes=f"{r[3]}GB {r[2]}-{r[4]}MHz")
                for r in alt_rams
            ]

    # ── Storage recommendation ─────────────────────────────────────────────
    if not storage:
        primary_stor, alt_stors = _select_storage(tier, usage_type, preferred_brand)
        if primary_stor:
            recommended_parts.append(RecommendedPart(
                category="Storage",
                model=primary_stor[0],
                brand=primary_stor[1],
                reasoning=f"{primary_stor[3]//1024}TB {primary_stor[2]} — {'fast NVMe for' if 'NVMe' in primary_stor[2] else 'reliable storage for'} {usage_type or 'general'} workloads",
                price_usd=primary_stor[4],
                compatibility_score=0.99,
            ))
            alternatives["Storage"] = [
                AlternativeOption(model=s[0], brand=s[1], price_usd=s[4], notes=f"{s[3]//1024}TB {s[2]}")
                for s in alt_stors
            ]

    # ── PSU recommendation (missing) ───────────────────────────────────────
    if not psu:
        primary_psu, alt_psus = _select_psu(cpu, gpu, tier, preferred_brand)
        if primary_psu:
            req = _calc_required_psu(cpu, gpu)
            recommended_parts.append(RecommendedPart(
                category="PSU",
                model=primary_psu[0],
                brand=primary_psu[1],
                reasoning=(
                    f"{primary_psu[2]}W {primary_psu[3]} PSU — "
                    f"system requires {req}W minimum (CPU+GPU+base × 1.30 headroom)"
                ),
                price_usd=primary_psu[4],
                compatibility_score=0.96,
            ))
            alternatives["PSU"] = [
                AlternativeOption(model=p[0], brand=p[1], price_usd=p[4], notes=f"{p[2]}W {p[3]}")
                for p in alt_psus
            ]
            psu = primary_psu[0]

    # ── PSU auto-upgrade (user-provided PSU may be underpowered) ───────────
    # This runs regardless of whether PSU was user-supplied or auto-filled.
    if psu and cpu and gpu:
        req         = _calc_required_psu(cpu, gpu)
        psu_watts   = _COMPAT_RULES.get("psu_wattage", {}).get(psu, 0)
        if psu_watts > 0 and psu_watts < req:
            # Auto-upgrade: find smallest PSU that covers required wattage
            upgrade_candidates = [
                p for p in _PSU_CATALOGUE if p[2] >= req
            ]
            upgrade_candidates.sort(key=lambda p: (p[2], p[4]))  # min watts, then price
            if upgrade_candidates:
                upgraded = upgrade_candidates[0]
                logger.warning(
                    "PSU auto-upgrade: '%s' (%dW) is underpowered for %dW load. "
                    "Replacing with '%s' (%dW).",
                    psu, psu_watts, req, upgraded[0], upgraded[2],
                )
                # Remove any existing PSU recommendation and replace
                recommended_parts = [
                    p for p in recommended_parts if p.category != "PSU"
                ]
                recommended_parts.append(RecommendedPart(
                    category="PSU",
                    model=upgraded[0],
                    brand=upgraded[1],
                    reasoning=(
                        f"AUTO-UPGRADED from '{psu}' ({psu_watts}W) — "
                        f"insufficient for {req}W load (CPU+GPU+base × 1.30). "
                        f"Minimum safe PSU: {upgraded[2]}W {upgraded[3]}."
                    ),
                    price_usd=upgraded[4],
                    compatibility_score=0.99,
                ))
                psu = upgraded[0]

    # ── Case recommendation ────────────────────────────────────────────────
    if not case:
        # Get MB form factor
        mb_ff = _COMPAT_RULES["motherboard_form_factor"].get(motherboard, "ATX") if motherboard else "ATX"
        primary_case, alt_cases = _select_case(mb_ff, gpu, tier, preferred_brand)
        if primary_case:
            recommended_parts.append(RecommendedPart(
                category="Case",
                model=primary_case[0],
                brand=primary_case[1],
                reasoning=f"Supports {mb_ff} form factor with {primary_case[3]}mm GPU clearance for {tier} build aesthetics",
                price_usd=primary_case[5],
                compatibility_score=0.97,
            ))
            alternatives["Case"] = [
                AlternativeOption(model=c[0], brand=c[1], price_usd=c[5], notes=f"{c[3]}mm GPU clearance")
                for c in alt_cases
            ]
            case = primary_case[0]

    # ── Cooler recommendation ──────────────────────────────────────────────
    if not cooler:
        case_clearance = _COMPAT_RULES["case_cooler_clearance_mm"].get(case) if case else None
        primary_cooler, alt_coolers = _select_cooler(cpu, tier, case_clearance, preferred_brand)
        if primary_cooler:
            aio_note = "AIO liquid cooler" if primary_cooler[4] else "air cooler"
            recommended_parts.append(RecommendedPart(
                category="Cooler",
                model=primary_cooler[0],
                brand=primary_cooler[1],
                reasoning=f"{aio_note} supporting up to {primary_cooler[3]}W TDP — appropriate for {tier} build thermal requirements",
                price_usd=primary_cooler[5],
                compatibility_score=0.95,
            ))
            alternatives["Cooler"] = [
                AlternativeOption(model=c[0], brand=c[1], price_usd=c[5], notes=f"{'AIO' if c[4] else 'Air'} cooler, {c[3]}W TDP support")
                for c in alt_coolers
            ]

    # ── Budget balance note ────────────────────────────────────────────────
    if budget_usd:
        est_total = sum(p.price_usd for p in recommended_parts)
        if est_total > budget_usd:
            over = est_total - budget_usd
            logger.info(
                "Recommended build (~$%.0f) exceeds budget ($%.0f) by $%.0f. "
                "Consider alternatives for cost reduction.",
                est_total, budget_usd, over,
            )

    # ── Proactive compatibility fix pass ──────────────────────────────────
    # Re-validate auto-filled components BEFORE returning.
    # If any auto-filled part creates a conflict, re-select it silently.
    # User-supplied conflicting parts are NOT swapped — they surface as errors.

    def _get_rec(category: str) -> Optional[RecommendedPart]:
        return next((p for p in recommended_parts if p.category == category), None)

    def _replace_rec(old: RecommendedPart, new: RecommendedPart) -> None:
        idx = recommended_parts.index(old)
        recommended_parts[idx] = new

    # Fix 1: Auto-filled Motherboard socket must match CPU
    if cpu:
        cpu_socket_needed = _COMPAT_RULES["cpu_socket_map"].get(cpu)
        mb_rec = _get_rec("Motherboard")
        if mb_rec and cpu_socket_needed:
            mb_socket_actual = _COMPAT_RULES["motherboard_socket_map"].get(mb_rec.model)
            if mb_socket_actual and mb_socket_actual != cpu_socket_needed:
                logger.warning(
                    "Compat fix: auto-filled MB '%s' (socket %s) conflicts with CPU '%s' (socket %s). Re-selecting.",
                    mb_rec.model, mb_socket_actual, cpu, cpu_socket_needed
                )
                fixed_mb, fixed_mb_alts = _select_mb(
                    cpu_socket_needed, ram_type or "DDR5", tier, preferred_brand
                )
                if fixed_mb:
                    _replace_rec(mb_rec, RecommendedPart(
                        category="Motherboard",
                        model=fixed_mb[0], brand=fixed_mb[1],
                        reasoning=(
                            f"Re-selected to match CPU socket {cpu_socket_needed} — "
                            f"previous auto-fill '{mb_rec.model}' would have been incompatible."
                        ),
                        price_usd=fixed_mb[5],
                        compatibility_score=0.98,
                    ))
                    motherboard = fixed_mb[0]

    # Fix 2: Auto-filled RAM type must match (now resolved) Motherboard
    if motherboard:
        mb_ram_types = _COMPAT_RULES.get("motherboard_ram_type", {}).get(motherboard)
        ram_rec = _get_rec("RAM")
        if ram_rec and mb_ram_types:
            # Infer RAM type from rec model name
            rec_ram_type = "DDR5" if "DDR5" in ram_rec.model else "DDR4" if "DDR4" in ram_rec.model else None
            if rec_ram_type and rec_ram_type not in mb_ram_types:
                correct_type = mb_ram_types[0]
                logger.warning(
                    "Compat fix: auto-filled RAM '%s' (%s) conflicts with MB '%s' (%s). Re-selecting.",
                    ram_rec.model, rec_ram_type, motherboard, correct_type
                )
                fixed_ram, fixed_ram_alts = _select_ram(correct_type, tier, budget_usd, usage_type, preferred_brand)
                if fixed_ram:
                    _replace_rec(ram_rec, RecommendedPart(
                        category="RAM",
                        model=fixed_ram[0], brand=fixed_ram[1],
                        reasoning=(
                            f"Re-selected {correct_type} to match motherboard '{motherboard}' — "
                            f"previous auto-fill was {rec_ram_type} which would have been incompatible."
                        ),
                        price_usd=fixed_ram[5],
                        compatibility_score=0.98,
                    ))

    # Fix 3: Auto-filled Case must support Motherboard form factor
    if motherboard:
        mb_ff = _COMPAT_RULES["motherboard_form_factor"].get(motherboard, "ATX")
        case_rec = _get_rec("Case")
        if case_rec:
            case_ffs = _COMPAT_RULES.get("case_supported_form_factors", {}).get(case_rec.model)
            if case_ffs and mb_ff not in case_ffs:
                logger.warning(
                    "Compat fix: auto-filled case '%s' doesn't support %s MB. Re-selecting.",
                    case_rec.model, mb_ff
                )
                gpu_now = gpu or ""
                fixed_case, fixed_case_alts = _select_case(mb_ff, gpu_now, tier, preferred_brand)
                if fixed_case:
                    _replace_rec(case_rec, RecommendedPart(
                        category="Case",
                        model=fixed_case[0], brand=fixed_case[1],
                        reasoning=(
                            f"Re-selected to support {mb_ff} form factor — "
                            f"previous auto-fill '{case_rec.model}' was incompatible."
                        ),
                        price_usd=fixed_case[5],
                        compatibility_score=0.97,
                    ))
                    case = fixed_case[0]

    # Fix 4: Auto-filled Cooler height must fit in Case
    if case:
        case_clear = _COMPAT_RULES.get("case_cooler_clearance_mm", {}).get(case)
        cooler_rec = _get_rec("Cooler")
        if cooler_rec and case_clear:
            cooler_h = _COMPAT_RULES.get("cooler_height_mm", {}).get(cooler_rec.model)
            if cooler_h and cooler_h > 30 and cooler_h > case_clear:
                logger.warning(
                    "Compat fix: auto-filled cooler '%s' (%dmm) exceeds case clearance %dmm. Re-selecting.",
                    cooler_rec.model, cooler_h, case_clear
                )
                fixed_cooler, _ = _select_cooler(cpu, tier, case_clear, preferred_brand)
                if fixed_cooler:
                    _replace_rec(cooler_rec, RecommendedPart(
                        category="Cooler",
                        model=fixed_cooler[0], brand=fixed_cooler[1],
                        reasoning=(
                            f"Re-selected to fit within {case_clear}mm case clearance — "
                            f"previous auto-fill '{cooler_rec.model}' ({cooler_h}mm) would not have fit."
                        ),
                        price_usd=fixed_cooler[5],
                        compatibility_score=0.96,
                    ))

    return RecommendationResult(
        recommended_parts=recommended_parts,
        alternatives=alternatives,
        inferred_tier=tier,
        tier_reasoning=tier_reasoning,
    )

