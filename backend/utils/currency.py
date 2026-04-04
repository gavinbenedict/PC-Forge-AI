"""
PCForge AI — Currency Conversion Layer

Live exchange rates from open.er-api.com (free, no key required).
Cached for 1 hour to avoid repeated network calls on Railway.
Falls back to static rates if the API is unreachable.
"""
from __future__ import annotations
import json
import logging
import time
import urllib.request
from typing import Dict

logger = logging.getLogger(__name__)

# ── Static fallback rates (USD base) ─────────────────────────────────────────

_STATIC_RATES: Dict[str, float] = {
    "USD": 1.00,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.37,
    "AUD": 1.53,
    "INR": 83.50,
    "JPY": 149.50,
}

_SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "C$",
    "AUD": "A$",
    "INR": "₹",
    "JPY": "¥",
}

SUPPORTED_CURRENCIES = list(_STATIC_RATES.keys())

# ── Live rate cache ───────────────────────────────────────────────────────────

_rate_cache: Dict[str, float] = {}
_cache_timestamp: float = 0.0
_CACHE_TTL = 3600.0          # 1 hour
_FX_URL = "https://open.er-api.com/v6/latest/USD"


def _get_rates() -> Dict[str, float]:
    """
    Return USD-base exchange rates.
    Fetches live data at most once per hour; falls back to static on any error.
    """
    global _rate_cache, _cache_timestamp

    now = time.monotonic()
    if _rate_cache and (now - _cache_timestamp) < _CACHE_TTL:
        return _rate_cache

    try:
        req = urllib.request.Request(
            _FX_URL,
            headers={"User-Agent": "PCForgeAI/2.0"},
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            payload = json.loads(resp.read().decode())
        if payload.get("result") == "success":
            rates = payload.get("rates", {})
            # Only keep currencies we actually support
            merged = dict(_STATIC_RATES)
            for code in _STATIC_RATES:
                if code in rates:
                    merged[code] = float(rates[code])
            _rate_cache = merged
            _cache_timestamp = now
            logger.info(
                "FX rates refreshed from live API (USD→INR=%.2f)", merged.get("INR", 0)
            )
            return _rate_cache
    except Exception as exc:
        logger.warning("FX API unavailable (%s) — using static rates", exc)

    # Return static as last resort (don't update cache timestamp so we retry next call)
    return _STATIC_RATES


# ── Public API ────────────────────────────────────────────────────────────────

def get_rate(currency: str) -> float:
    """Return the USD → currency exchange rate (e.g. USD→INR ≈ 83.5)."""
    return _get_rates().get(currency.upper(), 1.0)


def convert(amount_usd: float, to_currency: str) -> float:
    """Multiply a USD amount by the current exchange rate, return rounded value."""
    if to_currency.upper() == "USD":
        return round(amount_usd, 2)
    rate = get_rate(to_currency)
    return round(amount_usd * rate, 2)


def symbol(currency: str) -> str:
    """Return the display symbol for the given ISO currency code."""
    return _SYMBOLS.get(currency.upper(), "$")


def format_price(amount_usd: float, currency: str) -> str:
    """Human-readable price string (conversion applied)."""
    value = convert(amount_usd, currency)
    sym = symbol(currency)
    if currency.upper() in ("INR", "JPY"):
        return f"{sym}{value:,.0f}"
    return f"{sym}{value:,.2f}"
