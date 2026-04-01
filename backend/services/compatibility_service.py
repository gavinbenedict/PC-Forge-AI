"""
PCForge AI — Compatibility Service
Rule-based validation engine for PC build compatibility.
All rules mirror real-world constraints with severity levels.

Data resolution priority:
  1. Master Catalogue (catalogue.py) — when dataset is loaded
  2. JSON rules file (compatibility_rules.json) — always-available fallback
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.models.schemas import (
    CompatibilityIssue,
    CompatibilityReport,
    CompatibilityStatus,
)

logger = logging.getLogger(__name__)

# ─── Load Rules (JSON fallback) ───────────────────────────────────────────────

_RULES_PATH = Path(__file__).parent.parent / "data" / "compatibility_rules.json"

def _load_rules() -> Dict[str, Any]:
    with open(_RULES_PATH, "r") as f:
        return json.load(f)

_RULES: Dict[str, Any] = _load_rules()

# Base system power consumption (non-CPU/GPU components, estimated)
_BASE_SYSTEM_WATTS = 100  # Motherboard, RAM, storage, fans, etc.
_PSU_HEADROOM_FACTOR = 1.30  # 30% headroom minimum — mirrors recommendation_service


# ─── Catalogue Overlay Helpers ────────────────────────────────────────────────
# Each helper checks the catalogue first, falls back to JSON rules.

def _resolve_cpu_socket(cpu: str) -> Optional[str]:
    """Resolve CPU socket: catalogue → JSON rules."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_cpu_socket(cpu)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("cpu_socket_map", {}).get(cpu)


def _resolve_cpu_tdp(cpu: str) -> int:
    """Resolve CPU TDP: catalogue → JSON rules → default 125W."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_cpu_tdp(cpu)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("cpu_tdp_watts", {}).get(cpu, 125)


def _resolve_mb_socket(mb: str) -> Optional[str]:
    """Resolve motherboard socket: catalogue → JSON rules."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_mb_socket(mb)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("motherboard_socket_map", {}).get(mb)


def _resolve_mb_ram_types(mb: str) -> Optional[List[str]]:
    """Resolve supported RAM types: catalogue → JSON rules."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_mb_ram_types(mb)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("motherboard_ram_type", {}).get(mb)


def _resolve_mb_max_ram(mb: str) -> Optional[int]:
    """Resolve max RAM capacity: catalogue → JSON rules."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_mb_max_ram(mb)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("motherboard_max_ram_gb", {}).get(mb)


def _resolve_mb_form_factor(mb: str) -> Optional[str]:
    """Resolve motherboard form factor: catalogue → JSON rules."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_mb_form_factor(mb)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("motherboard_form_factor", {}).get(mb)


def _resolve_case_form_factors(case: str) -> Optional[List[str]]:
    """Resolve case supported form factors: catalogue → JSON rules."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_case_form_factors(case)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("case_supported_form_factors", {}).get(case)


def _resolve_gpu_length(gpu: str) -> Optional[int]:
    """Resolve GPU length: catalogue → JSON rules."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_gpu_length(gpu)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("gpu_length_mm", {}).get(gpu)


def _resolve_gpu_tdp(gpu: str) -> int:
    """Resolve GPU TDP: catalogue → JSON rules → default 200W."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_gpu_tdp(gpu)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("gpu_tdp_watts", {}).get(gpu, 200)


def _resolve_case_gpu_clearance(case: str) -> Optional[int]:
    """Resolve case GPU clearance: catalogue → JSON rules."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_case_gpu_clearance(case)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("case_gpu_clearance_mm", {}).get(case)


def _resolve_case_cooler_clearance(case: str) -> Optional[int]:
    """Resolve case cooler clearance: catalogue → JSON rules."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_case_cooler_clearance(case)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("case_cooler_clearance_mm", {}).get(case)


def _resolve_cooler_height(cooler: str) -> Optional[int]:
    """Resolve cooler height: catalogue → JSON rules."""
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            val = master_catalogue.get_cooler_height(cooler)
            if val:
                return val
    except Exception:
        pass
    return _RULES.get("cooler_height_mm", {}).get(cooler)



# ─── Individual Rule Checkers ─────────────────────────────────────────────────

def _check_cpu_motherboard_socket(
    cpu: Optional[str], motherboard: Optional[str]
) -> Tuple[bool, Optional[CompatibilityIssue]]:
    """Rule 1: CPU socket must match motherboard socket."""
    if not cpu or not motherboard:
        return True, None

    cpu_socket = _resolve_cpu_socket(cpu)
    mb_socket  = _resolve_mb_socket(motherboard)

    if not cpu_socket:
        return True, CompatibilityIssue(
            severity="warning",
            component="CPU",
            issue=f"CPU '{cpu}' not found in compatibility database — socket check skipped.",
            suggested_fix="Manually verify CPU socket compatibility with motherboard."
        )
    if not mb_socket:
        return True, CompatibilityIssue(
            severity="warning",
            component="Motherboard",
            issue=f"Motherboard '{motherboard}' not found in compatibility database.",
            suggested_fix="Manually verify motherboard socket compatibility with CPU."
        )

    if cpu_socket != mb_socket:
        return False, CompatibilityIssue(
            severity="error",
            component="CPU + Motherboard",
            issue=f"CPU socket {cpu_socket} ({cpu}) is incompatible with motherboard socket {mb_socket} ({motherboard}).",
            suggested_fix=f"Use a motherboard with {cpu_socket} socket, or choose a CPU that supports {mb_socket}."
        )
    return True, None


def _check_ram_type(
    motherboard: Optional[str], ram_type: Optional[str]
) -> Tuple[bool, Optional[CompatibilityIssue]]:
    """Rule 2: RAM type must match motherboard supported memory standard."""
    if not motherboard or not ram_type:
        return True, None

    supported = _resolve_mb_ram_types(motherboard)
    if not supported:
        return True, None  # Unknown MB — skip check

    ram_type_upper = ram_type.upper()
    if ram_type_upper not in supported:
        return False, CompatibilityIssue(
            severity="error",
            component="RAM + Motherboard",
            issue=f"RAM type {ram_type_upper} is not supported by {motherboard} (supports: {', '.join(supported)}).",
            suggested_fix=f"Use {', '.join(supported)} RAM modules with this motherboard."
        )
    return True, None


def _check_ram_capacity(
    motherboard: Optional[str], ram_size_gb: Optional[int]
) -> Tuple[bool, Optional[CompatibilityIssue]]:
    """Rule 3: RAM capacity must not exceed motherboard maximum."""
    if not motherboard or not ram_size_gb:
        return True, None

    max_gb = _resolve_mb_max_ram(motherboard)
    if not max_gb:
        return True, None

    if ram_size_gb > max_gb:
        return False, CompatibilityIssue(
            severity="error",
            component="RAM + Motherboard",
            issue=f"{ram_size_gb}GB RAM exceeds the maximum supported capacity ({max_gb}GB) for {motherboard}.",
            suggested_fix=f"Reduce RAM to {max_gb}GB or less, or choose a motherboard supporting {ram_size_gb}GB."
        )
    return True, None


def _check_case_motherboard_form_factor(
    case: Optional[str], motherboard: Optional[str]
) -> Tuple[bool, Optional[CompatibilityIssue]]:
    """Rule 4: Case must support motherboard form factor."""
    if not case or not motherboard:
        return True, None

    mb_ff = _resolve_mb_form_factor(motherboard)
    case_supported = _resolve_case_form_factors(case)

    if not mb_ff or not case_supported:
        return True, None

    if mb_ff not in case_supported:
        return False, CompatibilityIssue(
            severity="error",
            component="Case + Motherboard",
            issue=f"Case '{case}' does not support {mb_ff} form factor motherboards (supports: {', '.join(case_supported)}).",
            suggested_fix=f"Choose a case that supports {mb_ff} form factor, or use a smaller motherboard."
        )
    return True, None


def _check_gpu_case_clearance(
    gpu: Optional[str], case: Optional[str]
) -> Tuple[bool, Optional[CompatibilityIssue]]:
    """Rule 5: GPU length must fit within case GPU clearance."""
    if not gpu or not case:
        return True, None

    gpu_length    = _resolve_gpu_length(gpu)
    case_clearance = _resolve_case_gpu_clearance(case)

    if not gpu_length or not case_clearance:
        return True, None

    if gpu_length > case_clearance:
        return False, CompatibilityIssue(
            severity="error",
            component="GPU + Case",
            issue=f"GPU {gpu} ({gpu_length}mm) exceeds case clearance for {case} ({case_clearance}mm).",
            suggested_fix=f"Choose a case with GPU clearance ≥ {gpu_length}mm, or select a shorter GPU."
        )
    elif gpu_length > case_clearance * 0.9:
        return True, CompatibilityIssue(
            severity="warning",
            component="GPU + Case",
            issue=f"GPU {gpu} ({gpu_length}mm) fits but is very close to case limit ({case_clearance}mm). Verify before purchasing.",
            suggested_fix="Double check physical fit. Consider a case with more clearance for better airflow."
        )
    return True, None


def _parse_psu_wattage(psu_str: str) -> Optional[int]:
    """
    Extract numeric wattage from a PSU string.
    Strategy 1: Regex — match patterns like '850W', '1000 W', '650-watt'.
    Strategy 2: Catalogue lookup for wattage_w field.
    Returns None if wattage cannot be determined.
    """
    import re
    # Match e.g. "850W", "850w", "1000 W", "750-watt"
    m = re.search(r'(\d{3,4})\s*(?:w\b|watt)', psu_str, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Catalogue fallback — try to find PSU by name and read wattage_w
    try:
        from backend.data.catalogue import master_catalogue
        if master_catalogue.is_loaded():
            comp = master_catalogue.find_by_name(psu_str, "PSU")
            if comp and comp.wattage_w:
                return comp.wattage_w
    except Exception:
        pass

    return None


def _check_psu_wattage(
    cpu: Optional[str], gpu: Optional[str], psu_str: Optional[str]
) -> Tuple[bool, Optional[CompatibilityIssue]]:
    """Rule 6: PSU wattage must support total system TDP + 25% headroom."""
    if not psu_str:
        return True, None

    psu_watts = _parse_psu_wattage(psu_str)
    if not psu_watts:
        return True, CompatibilityIssue(
            severity="warning",
            component="PSU",
            issue="Could not parse PSU wattage from provided string.",
            suggested_fix="Specify PSU with wattage clearly, e.g. 'Corsair RM850x 850W'."
        )

    cpu_tdp = _resolve_cpu_tdp(cpu) if cpu else 125
    gpu_tdp = _resolve_gpu_tdp(gpu) if gpu else 200

    total_tdp = cpu_tdp + gpu_tdp + _BASE_SYSTEM_WATTS
    required_watts = int(total_tdp * _PSU_HEADROOM_FACTOR)

    if psu_watts < required_watts:
        return False, CompatibilityIssue(
            severity="error",
            component="PSU",
            issue=(
                f"PSU ({psu_watts}W) is insufficient. "
                f"System requires ~{required_watts}W (CPU: {cpu_tdp}W + GPU: {gpu_tdp}W + Base: {_BASE_SYSTEM_WATTS}W × 1.30 headroom)."
            ),
            suggested_fix=f"Upgrade to a PSU with at least {required_watts}W. Recommended: {_round_up_psu(required_watts)}W."
        )
    elif psu_watts < total_tdp * 1.1:
        return True, CompatibilityIssue(
            severity="warning",
            component="PSU",
            issue=f"PSU ({psu_watts}W) has minimal headroom. System TDP is ~{total_tdp}W.",
            suggested_fix="Consider a higher wattage PSU for long-term stability and future upgrades."
        )
    return True, None


def _round_up_psu(required: int) -> int:
    """Round up to nearest standard PSU wattage tier."""
    tiers = [550, 650, 750, 850, 1000, 1200, 1600]
    for tier in tiers:
        if tier >= required:
            return tier
    return tiers[-1]


def _check_cooler_case_clearance(
    cooler: Optional[str], case: Optional[str]
) -> Tuple[bool, Optional[CompatibilityIssue]]:
    """Rule 7: Cooler height must fit within case cooler clearance."""
    if not cooler or not case:
        return True, None

    cooler_height  = _resolve_cooler_height(cooler)
    case_clearance = _resolve_case_cooler_clearance(case)

    if not cooler_height or not case_clearance:
        return True, None

    # AIO coolers have radiator height, not tower height — skip height check
    if cooler_height <= 30:  # AIO radiator thickness
        return True, None

    if cooler_height > case_clearance:
        return False, CompatibilityIssue(
            severity="error",
            component="Cooler + Case",
            issue=f"Cooler '{cooler}' ({cooler_height}mm) exceeds case clearance for '{case}' ({case_clearance}mm).",
            suggested_fix=f"Choose a cooler under {case_clearance}mm height, or a case with more clearance."
        )
    return True, None


def _check_storage_interface(
    motherboard: Optional[str], storage_list: Optional[List[Dict]]
) -> List[CompatibilityIssue]:
    """Rule 8: Storage interface must be supported by motherboard."""
    issues = []
    if not storage_list:
        return issues
    # Most modern motherboards support both NVMe and SATA. 
    # Flag only PCIe 5.0 NVMe as requiring specific chipset support.
    for s in storage_list:
        if isinstance(s, dict) and s.get("type") in ("PCIe 5.0 NVMe",):
            if motherboard and "B550" in motherboard:
                issues.append(CompatibilityIssue(
                    severity="warning",
                    component="Storage + Motherboard",
                    issue=f"PCIe 5.0 NVMe storage may not be supported by {motherboard}.",
                    suggested_fix="Check motherboard M.2 slot specs. PCIe 5.0 requires Z790/X670 or newer chipsets."
                ))
    return issues


# ─── Main Checker ─────────────────────────────────────────────────────────────

def run_compatibility_check(
    cpu: Optional[str] = None,
    gpu: Optional[str] = None,
    motherboard: Optional[str] = None,
    ram: Optional[Dict[str, Any]] = None,
    storage: Optional[List[Dict]] = None,
    psu: Optional[str] = None,
    case: Optional[str] = None,
    cooler: Optional[str] = None,
) -> CompatibilityReport:
    """
    Run all compatibility rules against the provided build spec.
    Returns a full CompatibilityReport with status, issues, and passed checks.
    """
    issues: List[CompatibilityIssue] = []
    passed_checks: List[str] = []

    def run_check(name: str, result: Tuple[bool, Optional[CompatibilityIssue]]) -> None:
        ok, issue = result
        if issue:
            issues.append(issue)
        if ok and not issue:
            passed_checks.append(name)
        elif ok and issue and issue.severity == "warning":
            passed_checks.append(f"{name} (with warning)")

    # Rule 1: CPU ↔ Motherboard socket
    run_check("CPU ↔ Motherboard Socket", _check_cpu_motherboard_socket(cpu, motherboard))

    # Rule 2: RAM type ↔ Motherboard
    ram_type = ram.get("type") if ram else None
    ram_size = ram.get("size_gb") if ram else None
    run_check("RAM Type ↔ Motherboard", _check_ram_type(motherboard, ram_type))

    # Rule 3: RAM capacity
    run_check("RAM Capacity", _check_ram_capacity(motherboard, ram_size))

    # Rule 4: Case ↔ Motherboard form factor
    run_check("Case ↔ Motherboard Form Factor", _check_case_motherboard_form_factor(case, motherboard))

    # Rule 5: GPU ↔ Case clearance
    run_check("GPU Length ↔ Case Clearance", _check_gpu_case_clearance(gpu, case))

    # Rule 6: PSU wattage
    run_check("PSU Wattage + Headroom", _check_psu_wattage(cpu, gpu, psu))

    # Rule 7: Cooler ↔ Case clearance
    run_check("Cooler Height ↔ Case Clearance", _check_cooler_case_clearance(cooler, case))

    # Rule 8: Storage interface
    storage_issues = _check_storage_interface(motherboard, storage)
    for si in storage_issues:
        issues.append(si)

    # Determine overall status
    has_errors = any(i.severity == "error" for i in issues)
    has_warnings = any(i.severity == "warning" for i in issues)

    if has_errors:
        status: CompatibilityStatus = "invalid"
    elif has_warnings:
        status = "warning"
    else:
        status = "valid"

    total_checks = len(passed_checks) + len(issues)

    return CompatibilityReport(
        status=status,
        issues=issues,
        passed_checks=passed_checks,
        total_checks=total_checks,
    )
