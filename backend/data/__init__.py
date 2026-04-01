"""
PCForge AI — Data Module Init
Provides access to rules and catalogue data for internal services.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

_RULES_PATH = Path(__file__).parent / "compatibility_rules.json"
_RULES_CACHE: Dict[str, Any] = {}


def _get_rules() -> Dict[str, Any]:
    global _RULES_CACHE
    if not _RULES_CACHE:
        with open(_RULES_PATH, "r") as f:
            _RULES_CACHE = json.load(f)
    return _RULES_CACHE
