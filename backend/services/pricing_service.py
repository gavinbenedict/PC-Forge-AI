"""
PCForge AI — Pricing Service
Hybrid pricing layer: catalogue-first, then simulated price database fallback.

Data resolution order:
  1. Master Catalogue → exact/fuzzy match → base price + jitter
  2. Hardcoded _PRICE_DB → exact/partial match
  3. ML prediction fallback (handled by prediction_service)

Plug-in design: replace `_fetch_from_api()` with real API calls without
changing any other code.
"""
from __future__ import annotations
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.models.schemas import PricedPart, PriceSource

logger = logging.getLogger(__name__)

# ─── Simulated Price Database ─────────────────────────────────────────────────
# Format: { "Canonical Model Name": price_usd }
# ~300 SKUs across all categories with realistic 2024-2025 market prices.

_PRICE_DB: Dict[str, Dict[str, Any]] = {

    # ── CPUs ──────────────────────────────────────────────────────────────────
    "AMD Ryzen 9 7950X":        {"price": 549.99,  "brand": "AMD",   "category": "CPU", "store": "Newegg"},
    "AMD Ryzen 9 7900X":        {"price": 349.99,  "brand": "AMD",   "category": "CPU", "store": "Amazon"},
    "AMD Ryzen 9 7900":         {"price": 299.99,  "brand": "AMD",   "category": "CPU", "store": "Micro Center"},
    "AMD Ryzen 7 7700X":        {"price": 249.99,  "brand": "AMD",   "category": "CPU", "store": "Best Buy"},
    "AMD Ryzen 7 7700":         {"price": 199.99,  "brand": "AMD",   "category": "CPU", "store": "Newegg"},
    "AMD Ryzen 5 7600X":        {"price": 169.99,  "brand": "AMD",   "category": "CPU", "store": "Amazon"},
    "AMD Ryzen 5 7600":         {"price": 149.99,  "brand": "AMD",   "category": "CPU", "store": "Micro Center"},
    "AMD Ryzen 9 5950X":        {"price": 349.99,  "brand": "AMD",   "category": "CPU", "store": "Newegg"},
    "AMD Ryzen 9 5900X":        {"price": 249.99,  "brand": "AMD",   "category": "CPU", "store": "Amazon"},
    "AMD Ryzen 7 5800X":        {"price": 179.99,  "brand": "AMD",   "category": "CPU", "store": "B&H Photo"},
    "AMD Ryzen 7 5800X3D":      {"price": 229.99,  "brand": "AMD",   "category": "CPU", "store": "Amazon"},
    "AMD Ryzen 5 5600X":        {"price": 129.99,  "brand": "AMD",   "category": "CPU", "store": "Newegg"},
    "AMD Ryzen 5 5600":         {"price": 99.99,   "brand": "AMD",   "category": "CPU", "store": "Micro Center"},
    "Intel Core i9-14900K":     {"price": 569.99,  "brand": "Intel", "category": "CPU", "store": "B&H Photo"},
    "Intel Core i9-14900KF":    {"price": 529.99,  "brand": "Intel", "category": "CPU", "store": "Newegg"},
    "Intel Core i7-14700K":     {"price": 389.99,  "brand": "Intel", "category": "CPU", "store": "Amazon"},
    "Intel Core i7-14700KF":    {"price": 359.99,  "brand": "Intel", "category": "CPU", "store": "Micro Center"},
    "Intel Core i5-14600K":     {"price": 249.99,  "brand": "Intel", "category": "CPU", "store": "Best Buy"},
    "Intel Core i5-14600KF":    {"price": 229.99,  "brand": "Intel", "category": "CPU", "store": "Newegg"},
    "Intel Core i9-13900K":     {"price": 469.99,  "brand": "Intel", "category": "CPU", "store": "Amazon"},
    "Intel Core i9-13900KF":    {"price": 429.99,  "brand": "Intel", "category": "CPU", "store": "B&H Photo"},
    "Intel Core i7-13700K":     {"price": 329.99,  "brand": "Intel", "category": "CPU", "store": "Newegg"},
    "Intel Core i5-13600K":     {"price": 219.99,  "brand": "Intel", "category": "CPU", "store": "Amazon"},
    "Intel Core i5-13400F":     {"price": 159.99,  "brand": "Intel", "category": "CPU", "store": "Micro Center"},
    "Intel Core i3-13100F":     {"price": 89.99,   "brand": "Intel", "category": "CPU", "store": "Newegg"},
    "Intel Core i9-12900K":     {"price": 299.99,  "brand": "Intel", "category": "CPU", "store": "Amazon"},
    "Intel Core i7-12700K":     {"price": 229.99,  "brand": "Intel", "category": "CPU", "store": "B&H Photo"},
    "Intel Core i5-12600K":     {"price": 179.99,  "brand": "Intel", "category": "CPU", "store": "Newegg"},
    "Intel Core i5-12400F":     {"price": 129.99,  "brand": "Intel", "category": "CPU", "store": "Amazon"},

    # ── GPUs ──────────────────────────────────────────────────────────────────
    "NVIDIA RTX 4090":              {"price": 1599.99, "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA RTX 4080 Super":        {"price": 999.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 4080":              {"price": 899.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 4070 Ti Super":     {"price": 799.99,  "brand": "NVIDIA", "category": "GPU", "store": "B&H Photo"},
    "NVIDIA RTX 4070 Ti":           {"price": 749.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 4070 Super":        {"price": 599.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 4070":              {"price": 549.99,  "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA RTX 4060 Ti":           {"price": 399.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 4060":              {"price": 299.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 3090 Ti":           {"price": 799.99,  "brand": "NVIDIA", "category": "GPU", "store": "B&H Photo"},
    "NVIDIA RTX 3090":              {"price": 699.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 3080 Ti":           {"price": 549.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 3080":              {"price": 449.99,  "brand": "NVIDIA", "category": "GPU", "store": "Best Buy"},
    "NVIDIA RTX 3070 Ti":           {"price": 349.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "NVIDIA RTX 3070":              {"price": 299.99,  "brand": "NVIDIA", "category": "GPU", "store": "Amazon"},
    "NVIDIA RTX 3060 Ti":           {"price": 249.99,  "brand": "NVIDIA", "category": "GPU", "store": "B&H Photo"},
    "NVIDIA RTX 3060":              {"price": 199.99,  "brand": "NVIDIA", "category": "GPU", "store": "Newegg"},
    "AMD Radeon RX 7900 XTX":       {"price": 849.99,  "brand": "AMD",    "category": "GPU", "store": "Amazon"},
    "AMD Radeon RX 7900 XT":        {"price": 699.99,  "brand": "AMD",    "category": "GPU", "store": "Newegg"},
    "AMD Radeon RX 7800 XT":        {"price": 449.99,  "brand": "AMD",    "category": "GPU", "store": "Best Buy"},
    "AMD Radeon RX 7700 XT":        {"price": 349.99,  "brand": "AMD",    "category": "GPU", "store": "Amazon"},
    "AMD Radeon RX 7600":           {"price": 249.99,  "brand": "AMD",    "category": "GPU", "store": "Newegg"},
    "AMD Radeon RX 6950 XT":        {"price": 499.99,  "brand": "AMD",    "category": "GPU", "store": "B&H Photo"},
    "AMD Radeon RX 6800 XT":        {"price": 399.99,  "brand": "AMD",    "category": "GPU", "store": "Amazon"},
    "AMD Radeon RX 6700 XT":        {"price": 299.99,  "brand": "AMD",    "category": "GPU", "store": "Newegg"},
    "AMD Radeon RX 6600 XT":        {"price": 199.99,  "brand": "AMD",    "category": "GPU", "store": "Best Buy"},

    # ── Motherboards ──────────────────────────────────────────────────────────
    "ASUS ROG Crosshair X670E Hero":    {"price": 599.99, "brand": "ASUS",     "category": "Motherboard", "store": "Newegg"},
    "ASUS ROG Strix X670E-F Gaming":    {"price": 399.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "MSI MEG X670E ACE":                {"price": 549.99, "brand": "MSI",      "category": "Motherboard", "store": "B&H Photo"},
    "MSI MAG X670E Tomahawk":           {"price": 299.99, "brand": "MSI",      "category": "Motherboard", "store": "Newegg"},
    "Gigabyte X670E AORUS Master":      {"price": 499.99, "brand": "Gigabyte", "category": "Motherboard", "store": "Amazon"},
    "ASUS Prime X670-P":                {"price": 199.99, "brand": "ASUS",     "category": "Motherboard", "store": "Best Buy"},
    "ASRock X670E Taichi":              {"price": 449.99, "brand": "ASRock",   "category": "Motherboard", "store": "Newegg"},
    "ASUS ROG Strix B650E-F Gaming":    {"price": 299.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "MSI MAG B650 Tomahawk":            {"price": 199.99, "brand": "MSI",      "category": "Motherboard", "store": "Micro Center"},
    "Gigabyte B650 AORUS Elite AX":     {"price": 229.99, "brand": "Gigabyte", "category": "Motherboard", "store": "Newegg"},
    "ASUS Prime B650-PLUS":             {"price": 154.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "ASRock B650M Pro RS":              {"price": 139.99, "brand": "ASRock",   "category": "Motherboard", "store": "B&H Photo"},
    "ASUS ROG Crosshair VIII Hero":     {"price": 299.99, "brand": "ASUS",     "category": "Motherboard", "store": "Newegg"},
    "ASUS ROG Strix X570-E Gaming":     {"price": 259.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "MSI MEG X570 ACE":                 {"price": 299.99, "brand": "MSI",      "category": "Motherboard", "store": "B&H Photo"},
    "MSI MAG X570 Tomahawk":            {"price": 199.99, "brand": "MSI",      "category": "Motherboard", "store": "Newegg"},
    "Gigabyte X570 AORUS Master":       {"price": 279.99, "brand": "Gigabyte", "category": "Motherboard", "store": "Amazon"},
    "ASUS Prime X570-P":                {"price": 149.99, "brand": "ASUS",     "category": "Motherboard", "store": "Micro Center"},
    "ASUS ROG Strix B550-F Gaming":     {"price": 179.99, "brand": "ASUS",     "category": "Motherboard", "store": "Best Buy"},
    "MSI MAG B550 Tomahawk":            {"price": 149.99, "brand": "MSI",      "category": "Motherboard", "store": "Newegg"},
    "Gigabyte B550 AORUS Pro":          {"price": 159.99, "brand": "Gigabyte", "category": "Motherboard", "store": "Amazon"},
    "ASRock B550M Pro4":                {"price": 109.99, "brand": "ASRock",   "category": "Motherboard", "store": "Newegg"},
    "ASUS ROG Maximus Z790 Hero":       {"price": 699.99, "brand": "ASUS",     "category": "Motherboard", "store": "B&H Photo"},
    "ASUS ROG Strix Z790-E Gaming":     {"price": 449.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "MSI MEG Z790 ACE":                 {"price": 599.99, "brand": "MSI",      "category": "Motherboard", "store": "Newegg"},
    "MSI MAG Z790 Tomahawk":            {"price": 249.99, "brand": "MSI",      "category": "Motherboard", "store": "Micro Center"},
    "Gigabyte Z790 AORUS Master":       {"price": 499.99, "brand": "Gigabyte", "category": "Motherboard", "store": "Amazon"},
    "ASUS Prime Z790-P":                {"price": 189.99, "brand": "ASUS",     "category": "Motherboard", "store": "Best Buy"},
    "ASRock Z790 Taichi":               {"price": 399.99, "brand": "ASRock",   "category": "Motherboard", "store": "Newegg"},
    "ASUS ROG Strix Z690-E Gaming":     {"price": 349.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "MSI MAG Z690 Tomahawk":            {"price": 199.99, "brand": "MSI",      "category": "Motherboard", "store": "B&H Photo"},
    "Gigabyte Z690 AORUS Pro":          {"price": 229.99, "brand": "Gigabyte", "category": "Motherboard", "store": "Newegg"},
    "ASUS Prime B760-PLUS":             {"price": 149.99, "brand": "ASUS",     "category": "Motherboard", "store": "Amazon"},
    "MSI PRO B760M-A":                  {"price": 119.99, "brand": "MSI",      "category": "Motherboard", "store": "Micro Center"},
    "Gigabyte B760M DS3H":              {"price": 99.99,  "brand": "Gigabyte", "category": "Motherboard", "store": "Newegg"},

    # ── RAM ───────────────────────────────────────────────────────────────────
    "Corsair Vengeance DDR5-6000 32GB":     {"price": 109.99, "brand": "Corsair",  "category": "RAM", "store": "Amazon"},
    "Corsair Vengeance DDR5-6000 64GB":     {"price": 199.99, "brand": "Corsair",  "category": "RAM", "store": "Newegg"},
    "G.Skill Trident Z5 DDR5-6400 32GB":    {"price": 129.99, "brand": "G.Skill",  "category": "RAM", "store": "B&H Photo"},
    "G.Skill Trident Z5 DDR5-6400 64GB":    {"price": 239.99, "brand": "G.Skill",  "category": "RAM", "store": "Amazon"},
    "Kingston Fury Beast DDR5-5200 32GB":   {"price": 99.99,  "brand": "Kingston", "category": "RAM", "store": "Newegg"},
    "Kingston Fury Beast DDR5-5200 16GB":   {"price": 59.99,  "brand": "Kingston", "category": "RAM", "store": "Amazon"},
    "Teamgroup T-Force DDR5-6000 32GB":     {"price": 94.99,  "brand": "Teamgroup","category": "RAM", "store": "Newegg"},
    "Corsair Vengeance DDR4-3200 32GB":     {"price": 74.99,  "brand": "Corsair",  "category": "RAM", "store": "Amazon"},
    "Corsair Vengeance DDR4-3200 16GB":     {"price": 44.99,  "brand": "Corsair",  "category": "RAM", "store": "Newegg"},
    "G.Skill Ripjaws V DDR4-3600 32GB":     {"price": 79.99,  "brand": "G.Skill",  "category": "RAM", "store": "B&H Photo"},
    "G.Skill Ripjaws V DDR4-3600 16GB":     {"price": 49.99,  "brand": "G.Skill",  "category": "RAM", "store": "Amazon"},
    "Kingston Fury Beast DDR4-3200 32GB":   {"price": 69.99,  "brand": "Kingston", "category": "RAM", "store": "Newegg"},
    "Kingston Fury Beast DDR4-3200 16GB":   {"price": 39.99,  "brand": "Kingston", "category": "RAM", "store": "Amazon"},
    "Crucial Pro DDR5-5600 32GB":           {"price": 89.99,  "brand": "Crucial",  "category": "RAM", "store": "Best Buy"},
    "Crucial Ballistix DDR4-3600 32GB":     {"price": 84.99,  "brand": "Crucial",  "category": "RAM", "store": "Newegg"},

    # ── Storage ───────────────────────────────────────────────────────────────
    "Samsung 990 Pro 2TB NVMe":             {"price": 169.99, "brand": "Samsung",  "category": "Storage", "store": "Amazon"},
    "Samsung 990 Pro 1TB NVMe":             {"price": 99.99,  "brand": "Samsung",  "category": "Storage", "store": "Best Buy"},
    "Samsung 980 Pro 2TB NVMe":             {"price": 149.99, "brand": "Samsung",  "category": "Storage", "store": "Newegg"},
    "Samsung 980 Pro 1TB NVMe":             {"price": 89.99,  "brand": "Samsung",  "category": "Storage", "store": "Amazon"},
    "WD Black SN850X 2TB NVMe":             {"price": 159.99, "brand": "WD",       "category": "Storage", "store": "Newegg"},
    "WD Black SN850X 1TB NVMe":             {"price": 99.99,  "brand": "WD",       "category": "Storage", "store": "B&H Photo"},
    "Seagate FireCuda 530 2TB NVMe":        {"price": 179.99, "brand": "Seagate",  "category": "Storage", "store": "Amazon"},
    "Seagate FireCuda 530 1TB NVMe":        {"price": 109.99, "brand": "Seagate",  "category": "Storage", "store": "Newegg"},
    "Kingston KC3000 2TB NVMe":             {"price": 139.99, "brand": "Kingston", "category": "Storage", "store": "Amazon"},
    "Crucial P5 Plus 2TB NVMe":             {"price": 129.99, "brand": "Crucial",  "category": "Storage", "store": "Best Buy"},
    "Crucial P5 Plus 1TB NVMe":             {"price": 74.99,  "brand": "Crucial",  "category": "Storage", "store": "Newegg"},
    "Samsung 870 EVO 2TB SATA SSD":         {"price": 149.99, "brand": "Samsung",  "category": "Storage", "store": "Amazon"},
    "Samsung 870 EVO 1TB SATA SSD":         {"price": 79.99,  "brand": "Samsung",  "category": "Storage", "store": "Best Buy"},
    "Crucial MX500 2TB SATA SSD":           {"price": 99.99,  "brand": "Crucial",  "category": "Storage", "store": "Newegg"},
    "Crucial MX500 1TB SATA SSD":           {"price": 64.99,  "brand": "Crucial",  "category": "Storage", "store": "Amazon"},
    "WD Blue 4TB HDD":                      {"price": 79.99,  "brand": "WD",       "category": "Storage", "store": "Newegg"},
    "WD Blue 2TB HDD":                      {"price": 49.99,  "brand": "WD",       "category": "Storage", "store": "Amazon"},
    "Seagate Barracuda 4TB HDD":            {"price": 74.99,  "brand": "Seagate",  "category": "Storage", "store": "Best Buy"},
    "Seagate Barracuda 2TB HDD":            {"price": 44.99,  "brand": "Seagate",  "category": "Storage", "store": "Newegg"},
    "Samsung 990 EVO 1TB NVMe":             {"price": 84.99,  "brand": "Samsung",  "category": "Storage", "store": "Amazon"},

    # ── PSUs ──────────────────────────────────────────────────────────────────
    "Corsair RM1000x 1000W 80+ Gold":   {"price": 179.99, "brand": "Corsair",  "category": "PSU", "store": "Amazon"},
    "Corsair RM850x 850W 80+ Gold":     {"price": 149.99, "brand": "Corsair",  "category": "PSU", "store": "Newegg"},
    "Corsair RM750x 750W 80+ Gold":     {"price": 124.99, "brand": "Corsair",  "category": "PSU", "store": "Best Buy"},
    "Corsair RM650x 650W 80+ Gold":     {"price": 109.99, "brand": "Corsair",  "category": "PSU", "store": "Amazon"},
    "Seasonic Focus GX-1000 1000W 80+ Gold": {"price": 189.99,"brand": "Seasonic","category": "PSU","store": "Newegg"},
    "Seasonic Focus GX-850 850W 80+ Gold":  {"price": 154.99, "brand": "Seasonic","category": "PSU","store": "B&H Photo"},
    "Seasonic Focus GX-750 750W 80+ Gold":  {"price": 129.99, "brand": "Seasonic","category": "PSU","store": "Amazon"},
    "be quiet! Dark Power 13 1000W 80+ Titanium": {"price": 279.99,"brand": "be quiet!","category": "PSU","store": "Newegg"},
    "be quiet! Straight Power 11 850W 80+ Platinum": {"price": 159.99,"brand": "be quiet!","category": "PSU","store": "Amazon"},
    "be quiet! Pure Power 12M 750W 80+ Gold": {"price": 99.99,"brand": "be quiet!","category": "PSU","store": "Best Buy"},
    "EVGA SuperNOVA 1000 G6 1000W 80+ Gold": {"price": 169.99,"brand": "EVGA","category": "PSU","store": "Newegg"},
    "EVGA SuperNOVA 850 G6 850W 80+ Gold":   {"price": 139.99,"brand": "EVGA","category": "PSU","store": "Amazon"},
    "EVGA SuperNOVA 750 G6 750W 80+ Gold":   {"price": 119.99,"brand": "EVGA","category": "PSU","store": "B&H Photo"},
    "Fractal Design Ion+ 860W 80+ Platinum":  {"price": 149.99,"brand": "Fractal","category": "PSU","store": "Newegg"},
    "Thermaltake Toughpower GF3 1000W 80+ Gold": {"price": 159.99,"brand": "Thermaltake","category": "PSU","store": "Amazon"},
    "MSI MPG A850G 850W 80+ Gold":            {"price": 134.99,"brand": "MSI","category": "PSU","store": "Newegg"},
    "Gigabyte UD1000GM 1000W 80+ Gold":       {"price": 139.99,"brand": "Gigabyte","category": "PSU","store": "Best Buy"},
    "Corsair HX1200 1200W 80+ Platinum":      {"price": 229.99,"brand": "Corsair","category": "PSU","store": "Amazon"},
    "Corsair AX1600i 1600W 80+ Titanium":     {"price": 499.99,"brand": "Corsair","category": "PSU","store": "Newegg"},
    "Seasonic Prime TX-1000 1000W 80+ Titanium": {"price": 299.99,"brand": "Seasonic","category": "PSU","store": "B&H Photo"},

    # ── Cases ─────────────────────────────────────────────────────────────────
    "Lian Li PC-O11 Dynamic":          {"price": 139.99, "brand": "Lian Li",    "category": "Case", "store": "Newegg"},
    "Lian Li PC-O11 Dynamic EVO":      {"price": 169.99, "brand": "Lian Li",    "category": "Case", "store": "Amazon"},
    "Fractal Design Torrent":          {"price": 189.99, "brand": "Fractal",    "category": "Case", "store": "B&H Photo"},
    "Fractal Design Define 7":         {"price": 179.99, "brand": "Fractal",    "category": "Case", "store": "Newegg"},
    "Corsair 4000D Airflow":           {"price": 94.99,  "brand": "Corsair",    "category": "Case", "store": "Amazon"},
    "Corsair 5000D Airflow":           {"price": 174.99, "brand": "Corsair",    "category": "Case", "store": "Best Buy"},
    "NZXT H510":                       {"price": 79.99,  "brand": "NZXT",       "category": "Case", "store": "Newegg"},
    "NZXT H510 Elite":                 {"price": 149.99, "brand": "NZXT",       "category": "Case", "store": "Amazon"},
    "NZXT H7 Flow":                    {"price": 149.99, "brand": "NZXT",       "category": "Case", "store": "B&H Photo"},
    "Antec P120 Crystal":              {"price": 119.99, "brand": "Antec",      "category": "Case", "store": "Newegg"},
    "be quiet! Pure Base 500DX":       {"price": 109.99, "brand": "be quiet!",  "category": "Case", "store": "Amazon"},
    "be quiet! Dark Base Pro 901":     {"price": 269.99, "brand": "be quiet!",  "category": "Case", "store": "Newegg"},
    "Phanteks Enthoo Pro II":          {"price": 229.99, "brand": "Phanteks",   "category": "Case", "store": "B&H Photo"},
    "Thermaltake Core P6":             {"price": 199.99, "brand": "Thermaltake","category": "Case", "store": "Amazon"},
    "Silverstone FARA R1":             {"price": 69.99,  "brand": "Silverstone", "category": "Case", "store": "Newegg"},
    "Cooler Master HAF 700 EVO":       {"price": 249.99, "brand": "Cooler Master","category": "Case", "store": "Amazon"},
    "Cooler Master MasterBox TD500":   {"price": 89.99,  "brand": "Cooler Master","category": "Case", "store": "Best Buy"},
    "Deepcool CH510":                  {"price": 79.99,  "brand": "Deepcool",   "category": "Case", "store": "Newegg"},

    # ── Coolers ───────────────────────────────────────────────────────────────
    "Noctua NH-D15":                        {"price": 99.99,  "brand": "Noctua",       "category": "Cooler", "store": "Amazon"},
    "Noctua NH-U12S":                       {"price": 74.99,  "brand": "Noctua",       "category": "Cooler", "store": "Newegg"},
    "Noctua NH-U9S":                        {"price": 59.99,  "brand": "Noctua",       "category": "Cooler", "store": "B&H Photo"},
    "be quiet! Dark Rock Pro 4":            {"price": 89.99,  "brand": "be quiet!",    "category": "Cooler", "store": "Amazon"},
    "be quiet! Dark Rock 4":               {"price": 74.99,  "brand": "be quiet!",    "category": "Cooler", "store": "Newegg"},
    "be quiet! Shadow Rock 3":             {"price": 49.99,  "brand": "be quiet!",    "category": "Cooler", "store": "Amazon"},
    "Cooler Master Hyper 212":              {"price": 39.99,  "brand": "Cooler Master","category": "Cooler", "store": "Best Buy"},
    "DeepCool AK620":                       {"price": 59.99,  "brand": "DeepCool",     "category": "Cooler", "store": "Newegg"},
    "DeepCool AG400":                       {"price": 39.99,  "brand": "DeepCool",     "category": "Cooler", "store": "Amazon"},
    "Thermalright Peerless Assassin 120":   {"price": 44.99,  "brand": "Thermalright", "category": "Cooler", "store": "Newegg"},
    "ARCTIC Freezer 34 eSports":            {"price": 34.99,  "brand": "ARCTIC",       "category": "Cooler", "store": "Amazon"},
    "ID-COOLING SE-224-XT":                 {"price": 29.99,  "brand": "ID-COOLING",   "category": "Cooler", "store": "Newegg"},
    "Corsair iCUE H150i Elite":             {"price": 199.99, "brand": "Corsair",      "category": "Cooler", "store": "Amazon"},
    "Corsair iCUE H100i Elite":             {"price": 149.99, "brand": "Corsair",      "category": "Cooler", "store": "Best Buy"},
    "Cooler Master MasterLiquid ML360R":    {"price": 129.99, "brand": "Cooler Master","category": "Cooler", "store": "Newegg"},
    "NZXT Kraken X73":                      {"price": 179.99, "brand": "NZXT",         "category": "Cooler", "store": "Amazon"},
    "NZXT Kraken X53":                      {"price": 129.99, "brand": "NZXT",         "category": "Cooler", "store": "Newegg"},
    "Thermaltake TH360 ARGB":               {"price": 119.99, "brand": "Thermaltake",  "category": "Cooler", "store": "B&H Photo"},
    "DeepCool LT720":                       {"price": 149.99, "brand": "DeepCool",     "category": "Cooler", "store": "Amazon"},
    "Lian Li Galahad 360":                  {"price": 159.99, "brand": "Lian Li",      "category": "Cooler", "store": "Newegg"},

    # ── Monitors (Optional) ───────────────────────────────────────────────────
    "LG 27GP850-B 27\" 1440p 165Hz":       {"price": 279.99, "brand": "LG",       "category": "Monitor", "store": "Amazon"},
    "ASUS ROG Swift PG279QM 27\" 1440p 240Hz": {"price": 599.99, "brand": "ASUS", "category": "Monitor", "store": "Newegg"},
    "Samsung Odyssey G7 32\" 1440p 240Hz": {"price": 449.99, "brand": "Samsung",  "category": "Monitor", "store": "Best Buy"},
    "LG 32UN880-B 32\" 4K 60Hz":           {"price": 699.99, "brand": "LG",       "category": "Monitor", "store": "Amazon"},
    "Dell S2722DGM 27\" 1440p 165Hz":      {"price": 249.99, "brand": "Dell",     "category": "Monitor", "store": "Newegg"},
    "BenQ MOBIUZ EX2710Q 27\" 1440p 165Hz":{"price": 329.99, "brand": "BenQ",     "category": "Monitor", "store": "B&H Photo"},
    "MSI Optix MAG274QRF 27\" 1440p 165Hz":{"price": 299.99, "brand": "MSI",      "category": "Monitor", "store": "Newegg"},
    "Corsair Xeneon 32QHD165 32\" 1440p":  {"price": 499.99, "brand": "Corsair",  "category": "Monitor", "store": "Amazon"},
    "AOC 24G2 24\" 1080p 144Hz":           {"price": 149.99, "brand": "AOC",      "category": "Monitor", "store": "Newegg"},
    "ASUS TUF Gaming VG27AQ 27\" 1440p 165Hz": {"price": 349.99,"brand": "ASUS", "category": "Monitor", "store": "Best Buy"},
}

# ─── URL Generator (stores → category pages) ─────────────────────────────────

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
    """Add ±3% jitter to simulate live market fluctuation."""
    jitter = base_price * pct
    return round(random.uniform(base_price - jitter, base_price + jitter), 2)


# ─── Public Interface ─────────────────────────────────────────────────────────

class PricingService:
    """
    Simulated live pricing layer.
    
    Plug-in design: replace `_fetch_from_api()` with real API calls
    (PCPartPicker, Newegg) without changing any other code.
    """

    def get_price(self, model: str, category: str) -> Optional[PricedPart]:
        """
        Look up price for a specific model.
        Resolution order: catalogue → _PRICE_DB → None (triggers ML fallback).
        """
        # ── 1. Catalogue lookup ───────────────────────────────────────────────
        try:
            from backend.data.catalogue import master_catalogue
            if master_catalogue.is_loaded():
                comp = master_catalogue.find_by_name(model, category if category else None)
                if comp and comp.price_usd > 0:
                    store = _PRICE_DB.get(comp.full_name, {}).get("store", "Newegg")
                    return PricedPart(
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
                    )
        except Exception as exc:
            logger.debug("Catalogue lookup failed: %s", exc)

        # ── 2. Hardcoded _PRICE_DB lookup ─────────────────────────────────────
        data = _PRICE_DB.get(model)
        if data:
            return self._build_priced_part(model, data)

        # Strict partial match: ALL numeric tokens (model numbers) must match
        import re as _re
        def _num_tokens(s: str):
            return set(_re.findall(r'\d{3,}[a-z]*', s.lower()))

        query_nums = _num_tokens(model)
        for db_model, db_data in _PRICE_DB.items():
            if db_data["category"] != category:
                continue
            cand_nums = _num_tokens(db_model)
            # All numeric tokens from query must appear in candidate
            if query_nums and not query_nums.issubset(cand_nums):
                continue
            # Word-level overlap check (non-numeric significant words)
            q_words = {w.lower() for w in model.split() if len(w) > 3 and not w.isdigit()}
            c_words = {w.lower() for w in db_model.split() if len(w) > 3 and not w.isdigit()}
            if q_words & c_words:
                return self._build_priced_part(db_model, db_data)

        return None

    def _build_priced_part(self, model: str, data: Dict[str, Any]) -> PricedPart:
        price_with_jitter = _add_price_jitter(data["price"])
        return PricedPart(
            category=data["category"],
            brand=data["brand"],
            model=model,
            price_usd=price_with_jitter,
            currency="USD",
            store=data["store"],
            availability="In Stock",
            url=_build_url(model, data["store"]),
            last_updated=datetime.now(timezone.utc),
            source="simulated",
        )

    def get_all_by_category(self, category: str) -> List[PricedPart]:
        """Get all available parts in a category (used by recommendation engine)."""
        results = []
        # Try catalogue first
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
        # Fall back to hardcoded DB
        for model, data in _PRICE_DB.items():
            if data["category"] == category:
                results.append(self._build_priced_part(model, data))
        return results

    def get_base_price(self, model: str) -> Optional[float]:
        """Return raw base price without jitter (for ML training/comparison)."""
        data = _PRICE_DB.get(model)
        return data["price"] if data else None

    # ── Plug-in point for real APIs ─────────────────────────────────────────

    async def _fetch_from_api(self, model: str) -> Optional[Dict[str, Any]]:
        """
        [PLUG-IN POINT] Replace this method body with real API calls.
        Example integrations:
          - PCPartPicker (unofficial scraped API)
          - Newegg Product API
          - Amazon Product Advertising API
        
        Must return dict matching _PRICE_DB format or None.
        """
        # Currently delegates to simulated DB
        return _PRICE_DB.get(model)


# Singleton instance
pricing_service = PricingService()
