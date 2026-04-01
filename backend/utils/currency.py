"""
PCForge AI — Currency Conversion Layer
Applies to ALL price outputs. Rates are approximate and static
(replace with live FX API call for production).
"""
from __future__ import annotations
from typing import Dict

# Approximate mid-market rates vs USD (update periodically)
_RATES: Dict[str, float] = {
    "USD": 1.00,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.37,
    "AUD": 1.53,
    "INR": 83.50,
}

_SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "CAD": "CA$",
    "AUD": "AU$",
    "INR": "₹",
}

SUPPORTED_CURRENCIES = list(_RATES.keys())


def convert(amount_usd: float, to_currency: str) -> float:
    """Convert a USD amount to the target currency. Returns USD if unknown."""
    rate = _RATES.get(to_currency.upper(), 1.0)
    return round(amount_usd * rate, 2)


def symbol(currency: str) -> str:
    """Return the currency symbol for display."""
    return _SYMBOLS.get(currency.upper(), "$")


def format_price(amount_usd: float, currency: str) -> str:
    """Format a USD price into the target currency string."""
    converted = convert(amount_usd, currency)
    sym = symbol(currency)
    if currency.upper() == "INR":
        return f"{sym}{converted:,.0f}"
    return f"{sym}{converted:,.2f}"
