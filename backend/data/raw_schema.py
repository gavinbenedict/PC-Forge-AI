"""
PCForge AI — Raw Dataset Schema Definitions
============================================
Defines the expected field names for the raw input dataset (JSON or CSV).
Multiple field aliases are supported so common naming conventions all work.

Supported raw format:
  {
    "components": [ { ... }, ... ]
  }
OR flat list:
  [ { ... }, ... ]

Fields marked REQUIRED must be present OR derivable.
Fields marked OPTIONAL are used if present.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

# ─── Category Aliases ─────────────────────────────────────────────────────────
# Maps raw "type" values → canonical category name

CATEGORY_ALIASES: Dict[str, str] = {
    # CPU
    "cpu": "CPU", "processor": "CPU", "central processing unit": "CPU",
    # GPU
    "gpu": "GPU", "graphics card": "GPU", "graphics processing unit": "GPU",
    "video card": "GPU", "vga": "GPU",
    # Motherboard
    "motherboard": "Motherboard", "mobo": "Motherboard",
    "mainboard": "Motherboard", "mb": "Motherboard",
    # RAM
    "ram": "RAM", "memory": "RAM", "dram": "RAM",
    # Storage
    "storage": "Storage", "drive": "Storage", "ssd": "Storage",
    "hdd": "Storage", "nvme": "Storage", "hard drive": "Storage",
    "solid state drive": "Storage",
    # PSU
    "psu": "PSU", "power supply": "PSU", "power supply unit": "PSU",
    # Case
    "case": "Case", "chassis": "Case", "tower": "Case", "enclosure": "Case",
    # Cooler
    "cooler": "Cooler", "cpu cooler": "Cooler", "heatsink": "Cooler",
    "aio": "Cooler", "liquid cooler": "Cooler",
}

# ─── Field Alias Maps (raw field → canonical field) ───────────────────────────
# Each entry maps known raw field name variants to a single canonical name.

FIELD_ALIASES: Dict[str, List[str]] = {
    # ── Universal ──────────────────────────────────────────────────────────────
    "brand":        ["brand", "manufacturer", "make", "vendor", "mfr"],
    "model":        ["model", "model_name", "name", "product", "product_name",
                     "model_number", "part_name"],
    "price_usd":    ["price", "price_usd", "msrp", "cost", "retail_price",
                     "market_price", "usd_price"],
    "year":         ["year", "release_year", "launch_year", "introduced"],
    "type":         ["type", "category", "component_type", "part_type", "class"],

    # ── CPU ────────────────────────────────────────────────────────────────────
    "socket":          ["socket", "cpu_socket", "socket_type", "platform"],
    "cores":           ["cores", "core_count", "num_cores", "physical_cores",
                        "p_cores"],  # ignores E-cores for simplicity
    "threads":         ["threads", "thread_count", "num_threads", "logical_cores"],
    "base_clock_ghz":  ["base_clock", "base_clock_ghz", "base_freq", "base_frequency",
                        "clock_speed", "base_speed"],
    "boost_clock_ghz": ["boost_clock", "boost_clock_ghz", "boost_freq",
                        "boost_frequency", "max_clock", "max_boost_clock",
                        "turbo_clock"],
    "tdp_w":           ["tdp", "tdp_w", "power", "power_draw", "wattage",
                        "thermal_design_power", "max_tdp", "base_power"],
    "generation":      ["generation", "gen", "cpu_gen", "intel_gen", "amd_gen"],

    # ── GPU ────────────────────────────────────────────────────────────────────
    "vram_gb":         ["vram", "vram_gb", "memory", "gpu_memory", "video_memory",
                        "memory_gb", "vram_size", "dedicated_memory"],
    "memory_type":     ["memory_type", "vram_type", "memory_standard", "gddr"],
    "power_draw_w":    ["tdp", "power_draw", "power_draw_w", "gpu_tdp", "power",
                        "wattage", "tgp", "total_graphics_power"],
    "length_mm":       ["length", "length_mm", "card_length", "gpu_length",
                        "card_size", "size_mm"],
    "slot_width":      ["slot_width", "slots", "slot_size", "width"],

    # ── Motherboard ────────────────────────────────────────────────────────────
    "chipset":         ["chipset", "chipset_name", "platform_chipset"],
    "form_factor":     ["form_factor", "ff", "size", "atx_type", "board_size",
                        "mobo_size"],
    "ram_type":        ["ram_type", "memory_type", "supported_memory",
                        "memory_standard", "ddr_type"],
    "max_ram_gb":      ["max_ram", "max_ram_gb", "max_memory", "max_memory_gb",
                        "memory_capacity", "max_supported_memory"],

    # ── RAM ────────────────────────────────────────────────────────────────────
    "capacity_gb":     ["capacity", "capacity_gb", "size", "size_gb", "memory_gb",
                        "total_capacity"],
    "speed_mhz":       ["speed", "speed_mhz", "frequency", "clock_speed",
                        "memory_speed", "ddr_speed", "transfer_rate"],
    "modules":         ["modules", "sticks", "dimms", "kit_count", "kit"],

    # ── Storage ────────────────────────────────────────────────────────────────
    "interface":       ["interface", "protocol", "connection", "storage_type",
                        "storage_interface", "bus"],

    # ── PSU ────────────────────────────────────────────────────────────────────
    "wattage_w":       ["wattage", "wattage_w", "power", "rated_power",
                        "output_power", "capacity_w"],
    "efficiency":      ["efficiency", "rating", "80plus", "80_plus",
                        "efficiency_rating", "certification"],
    "modular":         ["modular", "is_modular", "modularity", "cable_management"],

    # ── Case ───────────────────────────────────────────────────────────────────
    "supported_form_factors":  ["supported_form_factors", "form_factors",
                                "compatibility", "supported_sizes", "mb_support"],
    "gpu_clearance_mm":        ["gpu_clearance", "gpu_clearance_mm",
                                "max_gpu_length", "gpu_length_max"],
    "cooler_clearance_mm":     ["cooler_clearance", "cooler_clearance_mm",
                                "max_cooler_height", "cpu_cooler_clearance"],

    # ── Cooler ─────────────────────────────────────────────────────────────────
    "cooler_type":    ["cooler_type", "type", "cooling_type",
                        "heatsink_type", "cooling_method"],
    "tdp_rating_w":   ["tdp_rating", "tdp_rating_w", "cooling_capacity",
                        "max_tdp", "thermal_capacity"],
    "height_mm":      ["height", "height_mm", "cooler_height",
                        "tower_height", "heatsink_height"],
    "radiator_mm":    ["radiator", "radiator_size", "rad_size",
                        "radiator_mm", "aio_size"],
}

# ─── Required Fields Per Category ─────────────────────────────────────────────
# If none of these can be resolved from the raw entry, the entry is discarded.

REQUIRED_FIELDS: Dict[str, List[str]] = {
    "CPU":          ["socket", "cores"],
    "GPU":          ["vram_gb", "power_draw_w"],
    "Motherboard":  ["socket", "chipset"],
    "RAM":          ["ram_type", "capacity_gb"],
    "Storage":      ["interface", "capacity_gb"],
    "PSU":          ["wattage_w"],
    "Case":         ["supported_form_factors"],
    "Cooler":       ["cooler_type"],
}

# ─── Relevance Filter Rules ────────────────────────────────────────────────────
MIN_RELEASE_YEAR = 2016  # Discard components older than this

# Categories where year is ignored (accessories don't age the same way)
YEAR_EXEMPT_CATEGORIES = {"Case", "Cooler", "PSU"}

# ─── Normalisation Helpers ────────────────────────────────────────────────────

FORM_FACTOR_ALIASES: Dict[str, str] = {
    "atx": "ATX", "standard atx": "ATX", "full atx": "ATX",
    "matx": "mATX", "micro atx": "mATX", "micro-atx": "mATX", "m-atx": "mATX",
    "eatx": "E-ATX", "extended atx": "E-ATX", "e-atx": "E-ATX",
    "itx": "ITX", "mini itx": "ITX", "mini-itx": "ITX", "mitx": "ITX",
    "xlatx": "XL-ATX", "xl atx": "XL-ATX",
}

EFFICIENCY_ALIASES: Dict[str, str] = {
    "80+": "80+ Standard", "80 plus": "80+ Standard", "standard": "80+ Standard",
    "bronze": "80+ Bronze", "80+ bronze": "80+ Bronze",
    "silver": "80+ Silver", "80+ silver": "80+ Silver",
    "gold": "80+ Gold", "80+ gold": "80+ Gold",
    "platinum": "80+ Platinum", "80+ platinum": "80+ Platinum",
    "titanium": "80+ Titanium", "80+ titanium": "80+ Titanium",
}

INTERFACE_ALIASES: Dict[str, str] = {
    "nvme": "NVMe Gen3", "m.2 nvme": "NVMe Gen3", "m2 nvme": "NVMe Gen3",
    "pcie 3.0": "NVMe Gen3", "pcie3": "NVMe Gen3", "gen3": "NVMe Gen3",
    "pcie 4.0": "NVMe Gen4", "pcie4": "NVMe Gen4", "gen4": "NVMe Gen4",
    "pcie 5.0": "NVMe Gen5", "pcie5": "NVMe Gen5", "gen5": "NVMe Gen5",
    "sata": "SATA SSD", "sata ssd": "SATA SSD", "2.5 sata": "SATA SSD",
    "sata iii": "SATA SSD", "sata3": "SATA SSD",
    "hdd": "HDD", "hard drive": "HDD", "sata hdd": "HDD",
}

RAM_TYPE_ALIASES: Dict[str, str] = {
    "ddr4": "DDR4", "ddr 4": "DDR4",
    "ddr5": "DDR5", "ddr 5": "DDR5",
}

SOCKET_ALIASES: Dict[str, str] = {
    "lga1151": "LGA1151", "1151": "LGA1151", "lga 1151": "LGA1151",
    "lga1200": "LGA1200", "1200": "LGA1200", "lga 1200": "LGA1200",
    "lga1700": "LGA1700", "1700": "LGA1700", "lga 1700": "LGA1700",
    "lga1851": "LGA1851", "1851": "LGA1851",
    "am4": "AM4", "socket am4": "AM4",
    "am5": "AM5", "socket am5": "AM5",
}


def resolve_field(raw: Dict[str, Any], canonical: str) -> Any:
    """
    Resolve a canonical field name from a raw dict using alias map.
    Returns None if no matching alias found.
    """
    aliases = FIELD_ALIASES.get(canonical, [canonical])
    for alias in aliases:
        # Try exact match first, then case-insensitive
        if alias in raw:
            return raw[alias]
        alias_lower = alias.lower()
        for key in raw:
            if key.lower() == alias_lower:
                return raw[key]
    return None


def resolve_category(raw_type: str) -> Optional[str]:
    """Resolve a raw type string to canonical category name."""
    return CATEGORY_ALIASES.get(str(raw_type).strip().lower())
