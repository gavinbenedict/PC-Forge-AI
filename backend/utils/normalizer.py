"""
PCForge AI — Input Normalizer
Cleans and standardizes raw user input into structured components.
Handles aliases, shorthand, and fuzzy matching.
"""
from __future__ import annotations
import re
from typing import Any, Dict, Optional
from difflib import get_close_matches


# ─── Known CPU Aliases ────────────────────────────────────────────────────────

CPU_ALIASES: Dict[str, str] = {
    # Shorthand → Full model
    "ryzen 9 7950x": "AMD Ryzen 9 7950X",
    "7950x": "AMD Ryzen 9 7950X",
    "ryzen 9 7900x": "AMD Ryzen 9 7900X",
    "7900x": "AMD Ryzen 9 7900X",
    "ryzen 7 7700x": "AMD Ryzen 7 7700X",
    "7700x": "AMD Ryzen 7 7700X",
    "ryzen 5 7600x": "AMD Ryzen 5 7600X",
    "7600x": "AMD Ryzen 5 7600X",
    "ryzen 9 5950x": "AMD Ryzen 9 5950X",
    "5950x": "AMD Ryzen 9 5950X",
    "ryzen 9 5900x": "AMD Ryzen 9 5900X",
    "5900x": "AMD Ryzen 9 5900X",
    "ryzen 7 5800x": "AMD Ryzen 7 5800X",
    "5800x": "AMD Ryzen 7 5800X",
    "ryzen 7 5800x3d": "AMD Ryzen 7 5800X3D",
    "5800x3d": "AMD Ryzen 7 5800X3D",
    "ryzen 5 5600x": "AMD Ryzen 5 5600X",
    "5600x": "AMD Ryzen 5 5600X",
    "i9 14900k": "Intel Core i9-14900K",
    "i9-14900k": "Intel Core i9-14900K",
    "14900k": "Intel Core i9-14900K",
    "i7 14700k": "Intel Core i7-14700K",
    "i7-14700k": "Intel Core i7-14700K",
    "14700k": "Intel Core i7-14700K",
    "i5 14600k": "Intel Core i5-14600K",
    "i5-14600k": "Intel Core i5-14600K",
    "14600k": "Intel Core i5-14600K",
    "i9 13900k": "Intel Core i9-13900K",
    "i9-13900k": "Intel Core i9-13900K",
    "13900k": "Intel Core i9-13900K",
    "i7 13700k": "Intel Core i7-13700K",
    "i7-13700k": "Intel Core i7-13700K",
    "13700k": "Intel Core i7-13700K",
    "i5 13600k": "Intel Core i5-13600K",
    "i5-13600k": "Intel Core i5-13600K",
    "13600k": "Intel Core i5-13600K",
    "i5 12600k": "Intel Core i5-12600K",
    "i5-12600k": "Intel Core i5-12600K",
    "12600k": "Intel Core i5-12600K",
}

GPU_ALIASES: Dict[str, str] = {
    "rtx 4090": "NVIDIA RTX 4090",
    "rtx4090": "NVIDIA RTX 4090",
    "4090": "NVIDIA RTX 4090",
    "rtx 4080 super": "NVIDIA RTX 4080 Super",
    "4080 super": "NVIDIA RTX 4080 Super",
    "rtx 4080": "NVIDIA RTX 4080",
    "4080": "NVIDIA RTX 4080",
    "rtx 4070 ti super": "NVIDIA RTX 4070 Ti Super",
    "4070 ti super": "NVIDIA RTX 4070 Ti Super",
    "rtx 4070 ti": "NVIDIA RTX 4070 Ti",
    "4070 ti": "NVIDIA RTX 4070 Ti",
    "rtx 4070 super": "NVIDIA RTX 4070 Super",
    "4070 super": "NVIDIA RTX 4070 Super",
    "rtx 4070": "NVIDIA RTX 4070",
    "4070": "NVIDIA RTX 4070",
    "rtx 4060 ti": "NVIDIA RTX 4060 Ti",
    "4060 ti": "NVIDIA RTX 4060 Ti",
    "rtx 4060": "NVIDIA RTX 4060",
    "4060": "NVIDIA RTX 4060",
    "rtx 3090": "NVIDIA RTX 3090",
    "3090": "NVIDIA RTX 3090",
    "rtx 3080": "NVIDIA RTX 3080",
    "3080": "NVIDIA RTX 3080",
    "rtx 3070": "NVIDIA RTX 3070",
    "3070": "NVIDIA RTX 3070",
    "rtx 3060": "NVIDIA RTX 3060",
    "3060": "NVIDIA RTX 3060",
    "rx 7900 xtx": "AMD Radeon RX 7900 XTX",
    "7900 xtx": "AMD Radeon RX 7900 XTX",
    "rx 7900 xt": "AMD Radeon RX 7900 XT",
    "7900 xt": "AMD Radeon RX 7900 XT",
    "rx 7800 xt": "AMD Radeon RX 7800 XT",
    "7800 xt": "AMD Radeon RX 7800 XT",
    "rx 7700 xt": "AMD Radeon RX 7700 XT",
    "7700 xt": "AMD Radeon RX 7700 XT",
    "rx 7600": "AMD Radeon RX 7600",
    "7600": "AMD Radeon RX 7600",
    "rx 6900 xt": "AMD Radeon RX 6950 XT",
    "rx 6800 xt": "AMD Radeon RX 6800 XT",
    "6800 xt": "AMD Radeon RX 6800 XT",
}

RAM_TYPE_ALIASES: Dict[str, str] = {
    "ddr 5": "DDR5",
    "ddr5": "DDR5",
    "ddr 4": "DDR4",
    "ddr4": "DDR4",
    "ddr 3": "DDR3",
    "ddr3": "DDR3",
}

STORAGE_TYPE_ALIASES: Dict[str, str] = {
    "nvme": "NVMe",
    "m.2 nvme": "NVMe",
    "m2 nvme": "NVMe",
    "ssd": "SATA SSD",
    "sata ssd": "SATA SSD",
    "sata": "SATA SSD",
    "hdd": "HDD",
    "hard drive": "HDD",
    "hard disk": "HDD",
    "pcie 5": "PCIe 5.0 NVMe",
    "pcie 4": "PCIe 4.0 NVMe",
    "pcie4": "PCIe 4.0 NVMe",
    "gen 5": "PCIe 5.0 NVMe",
    "gen 4": "PCIe 4.0 NVMe",
}


def _normalize_string(s: Optional[str]) -> Optional[str]:
    """Strip, lowercase, collapse whitespace."""
    if s is None:
        return None
    return re.sub(r"\s+", " ", s.strip())


def normalize_cpu(raw: Optional[str]) -> Optional[str]:
    """Resolve CPU aliases to canonical model name."""
    if not raw:
        return None
    s = _normalize_string(raw).lower()
    if s in CPU_ALIASES:
        return CPU_ALIASES[s]
    # Fuzzy match
    matches = get_close_matches(s, CPU_ALIASES.keys(), n=1, cutoff=0.7)
    if matches:
        return CPU_ALIASES[matches[0]]
    # Return title-cased original if no alias found
    return raw.strip()


def normalize_gpu(raw: Optional[str]) -> Optional[str]:
    """Resolve GPU aliases to canonical model name."""
    if not raw:
        return None
    s = _normalize_string(raw).lower()
    if s in GPU_ALIASES:
        return GPU_ALIASES[s]
    matches = get_close_matches(s, GPU_ALIASES.keys(), n=1, cutoff=0.7)
    if matches:
        return GPU_ALIASES[matches[0]]
    return raw.strip()


def normalize_ram_type(raw: Optional[str]) -> Optional[str]:
    """Normalize RAM type string."""
    if not raw:
        return None
    s = _normalize_string(raw).lower()
    return RAM_TYPE_ALIASES.get(s, raw.upper())


def normalize_storage_type(raw: Optional[str]) -> Optional[str]:
    """Normalize storage type string."""
    if not raw:
        return None
    s = _normalize_string(raw).lower()
    return STORAGE_TYPE_ALIASES.get(s, raw)


def parse_ram_string(raw: str) -> Dict[str, Any]:
    """
    Parse freeform RAM string like '32GB DDR5 6000MHz' into structured dict.
    Returns: {size_gb, type, speed_mhz}
    """
    result: Dict[str, Any] = {}
    # Size
    size_match = re.search(r"(\d+)\s*gb", raw, re.IGNORECASE)
    if size_match:
        result["size_gb"] = int(size_match.group(1))
    # Speed
    speed_match = re.search(r"(\d{4,5})\s*mhz", raw, re.IGNORECASE)
    if speed_match:
        result["speed_mhz"] = int(speed_match.group(1))
    # Type
    type_match = re.search(r"ddr\s*[345]", raw, re.IGNORECASE)
    if type_match:
        result["type"] = normalize_ram_type(type_match.group())
    return result


def parse_storage_string(raw: str) -> Dict[str, Any]:
    """
    Parse freeform storage string like '1TB NVMe' into structured dict.
    Returns: {capacity_gb, type}
    """
    result: Dict[str, Any] = {}
    # Capacity
    tb_match = re.search(r"(\d+(?:\.\d+)?)\s*tb", raw, re.IGNORECASE)
    gb_match = re.search(r"(\d+)\s*gb", raw, re.IGNORECASE)
    if tb_match:
        result["capacity_gb"] = int(float(tb_match.group(1)) * 1024)
    elif gb_match:
        result["capacity_gb"] = int(gb_match.group(1))
    # Type
    for keyword, storage_type in STORAGE_TYPE_ALIASES.items():
        if keyword in raw.lower():
            result["type"] = storage_type
            break
    return result


def normalize_build_spec(raw_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full normalizer pipeline. Accepts raw dict from API input,
    returns cleaned and structured dict.
    """
    spec = dict(raw_spec)

    # Normalize string components
    if spec.get("cpu"):
        spec["cpu"] = normalize_cpu(spec["cpu"])
    if spec.get("gpu"):
        spec["gpu"] = normalize_gpu(spec["gpu"])
    if spec.get("motherboard"):
        spec["motherboard"] = _normalize_string(spec["motherboard"])

    # Normalize RAM
    if isinstance(spec.get("ram"), dict):
        ram = spec["ram"]
        if ram.get("type"):
            ram["type"] = normalize_ram_type(ram["type"])
    elif isinstance(spec.get("ram"), str):
        spec["ram"] = parse_ram_string(spec["ram"])

    # Normalize storage list
    if isinstance(spec.get("storage"), list):
        normalized_storage = []
        for s in spec["storage"]:
            if isinstance(s, dict):
                if s.get("type"):
                    s["type"] = normalize_storage_type(s["type"])
                normalized_storage.append(s)
            elif isinstance(s, str):
                normalized_storage.append(parse_storage_string(s))
        spec["storage"] = normalized_storage
    elif isinstance(spec.get("storage"), str):
        spec["storage"] = [parse_storage_string(spec["storage"])]

    # Normalize usage_type to lowercase
    if spec.get("usage_type"):
        spec["usage_type"] = spec["usage_type"].lower().strip()

    # Normalize region to uppercase
    if spec.get("region"):
        spec["region"] = spec["region"].upper().strip()

    return spec
