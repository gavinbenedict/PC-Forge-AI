"""
PCForge AI — ML Price Prediction Service
XGBoost regression model for per-part price estimation.
Falls back to ML when no simulated/live price is available.
"""
from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

from backend.models.schemas import PricedPart, PriceRange
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent.parent / "data" / "models" / "price_model.pkl"
_ENCODER_PATH = Path(__file__).parent.parent / "data" / "models" / "feature_encoder.pkl"

# ─── Category Base Prices (fallback heuristics if model not loaded) ───────────

_CATEGORY_BASE = {
    "CPU":         {"budget": 120, "mid-range": 250, "high-end": 400, "enthusiast": 600},
    "GPU":         {"budget": 200, "mid-range": 450, "high-end": 800, "enthusiast": 1400},
    "Motherboard": {"budget": 120, "mid-range": 220, "high-end": 380, "enthusiast": 560},
    "RAM":         {"budget": 45,  "mid-range": 80,  "high-end": 140, "enthusiast": 220},
    "Storage":     {"budget": 70,  "mid-range": 100, "high-end": 160, "enthusiast": 200},
    "PSU":         {"budget": 90,  "mid-range": 130, "high-end": 165, "enthusiast": 220},
    "Case":        {"budget": 80,  "mid-range": 130, "high-end": 180, "enthusiast": 260},
    "Cooler":      {"budget": 35,  "mid-range": 65,  "high-end": 100, "enthusiast": 180},
    "Monitor":     {"budget": 150, "mid-range": 300, "high-end": 500, "enthusiast": 750},
}

# Price range multipliers: [min_factor, avg_factor, max_factor]
_RANGE_FACTORS = {
    "budget":     [0.80, 1.00, 1.25],
    "mid-range":  [0.82, 1.00, 1.22],
    "high-end":   [0.85, 1.00, 1.18],
    "enthusiast": [0.88, 1.00, 1.15],
}


def _encode_features(
    category: str,
    brand: str,
    tier: str,
    usage_type: Optional[str],
    specs: Dict[str, Any],
) -> np.ndarray:
    """
    Feature vector for ML model.
    Ordinal-encodes categorical features; uses numeric specs directly.
    """
    category_map = {"CPU": 0, "GPU": 1, "Motherboard": 2, "RAM": 3,
                    "Storage": 4, "PSU": 5, "Case": 6, "Cooler": 7, "Monitor": 8}
    tier_map = {"budget": 0, "mid-range": 1, "high-end": 2, "enthusiast": 3}
    usage_map = {"office": 0, "mixed": 1, "gaming": 2, "streaming": 3, "editing": 4, "workstation": 5}

    brand_map = {
        "AMD": 1, "Intel": 2, "NVIDIA": 3, "ASUS": 4, "MSI": 5, "Gigabyte": 6,
        "ASRock": 7, "Corsair": 8, "G.Skill": 9, "Kingston": 10, "Samsung": 11,
        "WD": 12, "Seagate": 13, "Crucial": 14, "Noctua": 15, "be quiet!": 16,
        "Lian Li": 17, "Fractal": 18, "NZXT": 19, "Seasonic": 20, "EVGA": 21,
    }

    return np.array([
        category_map.get(category, -1),
        brand_map.get(brand, 0),
        tier_map.get(tier, 1),
        usage_map.get(usage_type or "mixed", 1),
        specs.get("core_count", 8),
        specs.get("vram_gb", 0),
        specs.get("ram_size_gb", 0),
        specs.get("storage_gb", 0),
        specs.get("psu_wattage", 0),
        specs.get("tdp_watts", 125),
        specs.get("speed_mhz", 0),
        specs.get("base_clock_ghz", 0.0),
    ], dtype=np.float32)


class PredictionService:
    """
    ML-based price prediction service.
    
    - Loads XGBoost model from disk (trained by train_model.py)
    - Falls back to heuristic model if no trained model exists
    - Always labels predictions clearly as 'predicted'
    """

    def __init__(self):
        self._model = None
        self._model_loaded = False
        self._load_model()

    def _load_model(self) -> None:
        try:
            import joblib
            if _MODEL_PATH.exists():
                self._model = joblib.load(_MODEL_PATH)
                self._model_loaded = True
                logger.info("✅ ML price model loaded from %s", _MODEL_PATH)
            else:
                logger.warning("⚠️  Model not found at %s. Using heuristic fallback.", _MODEL_PATH)
        except Exception as e:
            logger.error("Failed to load ML model: %s", e)
            self._model_loaded = False

    def predict_price(
        self,
        category: str,
        brand: str,
        model_name: str,
        tier: str = "mid-range",
        usage_type: Optional[str] = None,
        specs: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, PriceRange]:
        """
        Predict price for a component.
        Returns (predicted_price, PriceRange).
        Always labeled source='predicted'.
        """
        specs = specs or {}

        if self._model_loaded and self._model is not None:
            return self._predict_with_model(category, brand, tier, usage_type, specs)
        else:
            return self._predict_heuristic(category, tier, specs)

    def _predict_with_model(
        self, category: str, brand: str, tier: str,
        usage_type: Optional[str], specs: Dict[str, Any]
    ) -> Tuple[float, PriceRange]:
        """Use trained XGBoost model for prediction."""
        try:
            features = _encode_features(category, brand, tier, usage_type, specs)
            features_2d = features.reshape(1, -1)
            predicted = float(self._model.predict(features_2d)[0])
            predicted = max(10.0, round(predicted, 2))
            
            factors = _RANGE_FACTORS.get(tier, [0.82, 1.00, 1.20])
            price_range = PriceRange(
                min_price=round(predicted * factors[0], 2),
                average_price=round(predicted * factors[1], 2),
                max_price=round(predicted * factors[2], 2),
            )
            return predicted, price_range
        except Exception as e:
            logger.error("Model prediction failed: %s. Falling back to heuristic.", e)
            return self._predict_heuristic(category, tier, specs)

    def _predict_heuristic(
        self, category: str, tier: str, specs: Dict[str, Any]
    ) -> Tuple[float, PriceRange]:
        """Heuristic price estimation based on category/tier/specs."""
        base = _CATEGORY_BASE.get(category, {}).get(tier, 150)

        # Spec-based adjustments
        if category == "RAM":
            size_gb = specs.get("ram_size_gb", 32)
            speed_bonus = (specs.get("speed_mhz", 3200) - 3200) / 1000 * 10
            base = base * (size_gb / 32) + speed_bonus
        elif category == "Storage":
            cap_gb = specs.get("storage_gb", 1024)
            base = base * (cap_gb / 1024)
        elif category == "PSU":
            watts = specs.get("psu_wattage", 750)
            base = base * (watts / 750)
        elif category == "CPU":
            cores = specs.get("core_count", 8)
            base = base * (0.6 + (cores / 32) * 0.8)
        elif category == "GPU":
            vram = specs.get("vram_gb", 8)
            base = base * (0.5 + (vram / 24) * 0.8)

        predicted = round(max(10.0, base), 2)
        factors = _RANGE_FACTORS.get(tier, [0.82, 1.00, 1.20])
        price_range = PriceRange(
            min_price=round(predicted * factors[0], 2),
            average_price=round(predicted * factors[1], 2),
            max_price=round(predicted * factors[2], 2),
        )
        return predicted, price_range

    def build_priced_part_predicted(
        self,
        category: str,
        brand: str,
        model_name: str,
        tier: str = "mid-range",
        usage_type: Optional[str] = None,
        specs: Optional[Dict[str, Any]] = None,
    ) -> PricedPart:
        """Build a full PricedPart marked as 'predicted'."""
        price, price_range = self.predict_price(
            category, brand, model_name, tier, usage_type, specs
        )
        return PricedPart(
            category=category,
            brand=brand,
            model=model_name,
            price_usd=price,
            currency="USD",
            store="Market Estimate",
            availability="Estimated",
            url=f"https://www.google.com/search?q={model_name.replace(' ', '+')}+price",
            last_updated=datetime.now(timezone.utc),
            source="predicted",
            predicted_range=price_range,
        )


# Singleton
prediction_service = PredictionService()
