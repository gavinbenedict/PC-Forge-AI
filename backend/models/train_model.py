"""
PCForge AI — ML Model Training Script
Generates synthetic dataset and trains XGBoost price regression model.
Run: python -m backend.models.train_model

Output: data/models/price_model.pkl
"""
from __future__ import annotations
import logging
import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = OUTPUT_DIR / "price_model.pkl"
CSV_PATH = Path(__file__).parent.parent.parent / "data" / "raw" / "synthetic_components.csv"
CSV_PATH.parent.mkdir(parents=True, exist_ok=True)


# ─── Synthetic Dataset Generation ─────────────────────────────────────────────

COMPONENTS = [
    # CPU entries: (category, brand, model, tier, usage, cores, threads, base_ghz, vram, ram_size, storage, psu_w, tdp, price)
    ("CPU", "AMD",   "Ryzen 5 5600",    "budget",     "gaming",     6,  12, 3.5, 0, 0, 0, 0, 65,  99.99),
    ("CPU", "AMD",   "Ryzen 5 7600",    "budget",     "gaming",     6,  12, 3.8, 0, 0, 0, 0, 65, 149.99),
    ("CPU", "AMD",   "Ryzen 7 7700X",   "mid-range",  "gaming",     8,  16, 4.5, 0, 0, 0, 0, 105, 249.99),
    ("CPU", "Intel", "Core i5-13400F",  "budget",     "mixed",      10, 16, 2.5, 0, 0, 0, 0, 65, 159.99),
    ("CPU", "Intel", "Core i5-13600K",  "mid-range",  "gaming",     14, 20, 3.5, 0, 0, 0, 0, 181, 219.99),
    ("CPU", "Intel", "Core i7-13700K",  "high-end",   "streaming",  16, 24, 3.4, 0, 0, 0, 0, 253, 329.99),
    ("CPU", "Intel", "Core i9-13900K",  "enthusiast", "workstation",24, 32, 3.0, 0, 0, 0, 0, 253, 469.99),
    ("CPU", "AMD",   "Ryzen 9 7950X",   "enthusiast", "workstation",16, 32, 4.5, 0, 0, 0, 0, 170, 549.99),
    ("CPU", "AMD",   "Ryzen 9 7900X",   "high-end",   "editing",    12, 24, 4.7, 0, 0, 0, 0, 170, 349.99),
    ("CPU", "Intel", "Core i5-14600K",  "mid-range",  "gaming",     14, 20, 3.5, 0, 0, 0, 0, 181, 249.99),
    ("CPU", "Intel", "Core i7-14700K",  "high-end",   "streaming",  20, 28, 3.4, 0, 0, 0, 0, 253, 389.99),
    ("CPU", "Intel", "Core i9-14900K",  "enthusiast", "workstation",24, 32, 3.2, 0, 0, 0, 0, 253, 569.99),
    ("CPU", "AMD",   "Ryzen 7 5800X3D", "mid-range",  "gaming",     8,  16, 3.4, 0, 0, 0, 0, 105, 229.99),
    ("CPU", "AMD",   "Ryzen 5 5600X",   "budget",     "gaming",     6,  12, 3.7, 0, 0, 0, 0, 65, 129.99),
    ("CPU", "AMD",   "Ryzen 9 5950X",   "enthusiast", "workstation",16, 32, 3.4, 0, 0, 0, 0, 105, 349.99),
    ("CPU", "AMD",   "Ryzen 7 7700",    "mid-range",  "gaming",     8,  16, 3.8, 0, 0, 0, 0, 65, 199.99),
    ("CPU", "Intel", "Core i3-13100F",  "budget",     "office",     4,  8,  3.4, 0, 0, 0, 0, 58,  89.99),
    ("CPU", "Intel", "Core i5-12400F",  "budget",     "gaming",     6,  12, 2.6, 0, 0, 0, 0, 65, 129.99),
    ("CPU", "Intel", "Core i5-12600K",  "mid-range",  "gaming",     10, 16, 3.7, 0, 0, 0, 0, 150, 179.99),
    ("CPU", "Intel", "Core i9-12900K",  "enthusiast", "workstation",16, 24, 3.2, 0, 0, 0, 0, 241, 299.99),

    # GPU entries
    ("GPU", "NVIDIA", "RTX 4090",        "enthusiast", "gaming",    0, 0, 0, 24, 0, 0, 0, 450, 1599.99),
    ("GPU", "NVIDIA", "RTX 4080 Super",  "enthusiast", "gaming",    0, 0, 0, 16, 0, 0, 0, 320,  999.99),
    ("GPU", "NVIDIA", "RTX 4080",        "enthusiast", "gaming",    0, 0, 0, 16, 0, 0, 0, 320,  899.99),
    ("GPU", "NVIDIA", "RTX 4070 Ti Super","high-end",  "gaming",    0, 0, 0, 16, 0, 0, 0, 285,  799.99),
    ("GPU", "NVIDIA", "RTX 4070 Ti",     "high-end",  "gaming",     0, 0, 0, 12, 0, 0, 0, 285,  749.99),
    ("GPU", "NVIDIA", "RTX 4070 Super",  "high-end",  "gaming",     0, 0, 0, 12, 0, 0, 0, 220,  599.99),
    ("GPU", "NVIDIA", "RTX 4070",        "mid-range", "gaming",     0, 0, 0, 12, 0, 0, 0, 200,  549.99),
    ("GPU", "NVIDIA", "RTX 4060 Ti",     "mid-range", "gaming",     0, 0, 0, 8,  0, 0, 0, 165,  399.99),
    ("GPU", "NVIDIA", "RTX 4060",        "budget",    "gaming",     0, 0, 0, 8,  0, 0, 0, 115,  299.99),
    ("GPU", "NVIDIA", "RTX 3090",        "enthusiast","gaming",     0, 0, 0, 24, 0, 0, 0, 350,  699.99),
    ("GPU", "NVIDIA", "RTX 3080",        "high-end",  "gaming",     0, 0, 0, 10, 0, 0, 0, 320,  449.99),
    ("GPU", "NVIDIA", "RTX 3070",        "mid-range", "gaming",     0, 0, 0, 8,  0, 0, 0, 220,  299.99),
    ("GPU", "NVIDIA", "RTX 3060",        "budget",    "gaming",     0, 0, 0, 12, 0, 0, 0, 170,  199.99),
    ("GPU", "AMD",    "RX 7900 XTX",     "enthusiast","gaming",     0, 0, 0, 24, 0, 0, 0, 355,  849.99),
    ("GPU", "AMD",    "RX 7900 XT",      "high-end",  "gaming",     0, 0, 0, 20, 0, 0, 0, 300,  699.99),
    ("GPU", "AMD",    "RX 7800 XT",      "mid-range", "gaming",     0, 0, 0, 16, 0, 0, 0, 263,  449.99),
    ("GPU", "AMD",    "RX 7700 XT",      "mid-range", "gaming",     0, 0, 0, 12, 0, 0, 0, 245,  349.99),
    ("GPU", "AMD",    "RX 7600",         "budget",    "gaming",     0, 0, 0, 8,  0, 0, 0, 165,  249.99),
    ("GPU", "AMD",    "RX 6800 XT",      "high-end",  "gaming",     0, 0, 0, 16, 0, 0, 0, 300,  399.99),
    ("GPU", "AMD",    "RX 6700 XT",      "mid-range", "gaming",     0, 0, 0, 12, 0, 0, 0, 230,  299.99),

    # Motherboard
    ("Motherboard", "ASUS",     "ROG Crosshair X670E Hero",  "enthusiast","gaming",0,0,0,0,0,0,0,0,599.99),
    ("Motherboard", "MSI",      "MEG X670E ACE",             "enthusiast","workstation",0,0,0,0,0,0,0,0,549.99),
    ("Motherboard", "Gigabyte", "X670E AORUS Master",        "enthusiast","editing",0,0,0,0,0,0,0,0,499.99),
    ("Motherboard", "ASUS",     "ROG Strix X670E-F Gaming",  "high-end", "gaming",0,0,0,0,0,0,0,0,399.99),
    ("Motherboard", "MSI",      "MAG X670E Tomahawk",        "high-end", "gaming",0,0,0,0,0,0,0,0,299.99),
    ("Motherboard", "ASUS",     "ROG Strix B650E-F Gaming",  "mid-range","gaming",0,0,0,0,0,0,0,0,299.99),
    ("Motherboard", "MSI",      "MAG B650 Tomahawk",         "mid-range","gaming",0,0,0,0,0,0,0,0,199.99),
    ("Motherboard", "Gigabyte", "B650 AORUS Elite AX",       "mid-range","gaming",0,0,0,0,0,0,0,0,229.99),
    ("Motherboard", "ASUS",     "Prime B650-PLUS",           "budget",   "gaming",0,0,0,0,0,0,0,0,154.99),
    ("Motherboard", "ASRock",   "B650M Pro RS",              "budget",   "office",0,0,0,0,0,0,0,0,139.99),
    ("Motherboard", "ASUS",     "ROG Maximus Z790 Hero",     "enthusiast","gaming",0,0,0,0,0,0,0,0,699.99),
    ("Motherboard", "MSI",      "MEG Z790 ACE",              "enthusiast","workstation",0,0,0,0,0,0,0,0,599.99),
    ("Motherboard", "ASUS",     "ROG Strix Z790-E Gaming",   "high-end", "gaming",0,0,0,0,0,0,0,0,449.99),
    ("Motherboard", "MSI",      "MAG Z790 Tomahawk",         "mid-range","gaming",0,0,0,0,0,0,0,0,249.99),
    ("Motherboard", "ASUS",     "Prime Z790-P",              "mid-range","gaming",0,0,0,0,0,0,0,0,189.99),
    ("Motherboard", "Gigabyte", "B760M DS3H",                "budget",   "office",0,0,0,0,0,0,0,0,99.99),

    # RAM
    ("RAM", "Kingston", "Fury Beast DDR4-3200 16GB", "budget",    "gaming",    0,0,0,0,16,0,0,0,39.99),
    ("RAM", "Corsair",  "Vengeance DDR4-3200 16GB",  "budget",    "gaming",    0,0,0,0,16,0,0,0,44.99),
    ("RAM", "G.Skill",  "Ripjaws V DDR4-3600 16GB",  "budget",    "gaming",    0,0,0,0,16,0,0,0,49.99),
    ("RAM", "Kingston", "Fury Beast DDR4-3200 32GB",  "mid-range", "gaming",    0,0,0,0,32,0,0,0,69.99),
    ("RAM", "Corsair",  "Vengeance DDR4-3200 32GB",  "mid-range", "gaming",    0,0,0,0,32,0,0,0,74.99),
    ("RAM", "G.Skill",  "Ripjaws V DDR4-3600 32GB",  "mid-range", "editing",   0,0,0,0,32,0,0,0,79.99),
    ("RAM", "Kingston", "Fury Beast DDR5-5200 32GB",  "mid-range", "gaming",    0,0,0,0,32,0,0,0,99.99),
    ("RAM", "Corsair",  "Vengeance DDR5-6000 32GB",  "mid-range", "gaming",    0,0,0,0,32,0,0,0,109.99),
    ("RAM", "G.Skill",  "Trident Z5 DDR5-6400 32GB", "high-end",  "editing",   0,0,0,0,32,0,0,0,129.99),
    ("RAM", "Corsair",  "Vengeance DDR5-6000 64GB",  "high-end",  "editing",   0,0,0,0,64,0,0,0,199.99),
    ("RAM", "G.Skill",  "Trident Z5 DDR5-6400 64GB", "enthusiast","workstation",0,0,0,0,64,0,0,0,239.99),
    ("RAM", "Crucial",  "Pro DDR5-5600 32GB",         "mid-range", "gaming",    0,0,0,0,32,0,0,0,89.99),

    # Storage
    ("Storage", "Crucial",  "MX500 1TB SATA SSD",    "budget",    "gaming",  0,0,0,0,0,1024,0,0,64.99),
    ("Storage", "Samsung",  "870 EVO 1TB SATA SSD",  "budget",    "gaming",  0,0,0,0,0,1024,0,0,79.99),
    ("Storage", "WD",       "Black SN850X 1TB NVMe", "mid-range", "gaming",  0,0,0,0,0,1024,0,0,99.99),
    ("Storage", "Samsung",  "980 Pro 1TB NVMe",      "mid-range", "gaming",  0,0,0,0,0,1024,0,0,89.99),
    ("Storage", "Samsung",  "990 Pro 1TB NVMe",      "mid-range", "gaming",  0,0,0,0,0,1024,0,0,99.99),
    ("Storage", "Samsung",  "980 Pro 2TB NVMe",      "high-end",  "editing", 0,0,0,0,0,2048,0,0,149.99),
    ("Storage", "WD",       "Black SN850X 2TB NVMe", "high-end",  "editing", 0,0,0,0,0,2048,0,0,159.99),
    ("Storage", "Samsung",  "990 Pro 2TB NVMe",      "high-end",  "editing", 0,0,0,0,0,2048,0,0,169.99),
    ("Storage", "WD",       "Blue 4TB HDD",          "budget",    "office",  0,0,0,0,0,4096,0,0,79.99),
    ("Storage", "Seagate",  "Barracuda 4TB HDD",     "budget",    "office",  0,0,0,0,0,4096,0,0,74.99),

    # PSU
    ("PSU", "Corsair",  "RM650x 650W 80+ Gold",   "budget",    "gaming",  0,0,0,0,0,0,650,0,109.99),
    ("PSU", "Corsair",  "RM750x 750W 80+ Gold",   "mid-range", "gaming",  0,0,0,0,0,0,750,0,124.99),
    ("PSU", "Corsair",  "RM850x 850W 80+ Gold",   "high-end",  "gaming",  0,0,0,0,0,0,850,0,149.99),
    ("PSU", "Corsair",  "RM1000x 1000W 80+ Gold", "enthusiast","gaming",  0,0,0,0,0,0,1000,0,179.99),
    ("PSU", "Seasonic", "Focus GX-750 750W",      "mid-range", "gaming",  0,0,0,0,0,0,750,0,129.99),
    ("PSU", "Seasonic", "Focus GX-850 850W",      "high-end",  "gaming",  0,0,0,0,0,0,850,0,154.99),
    ("PSU", "Seasonic", "Focus GX-1000 1000W",    "enthusiast","gaming",  0,0,0,0,0,0,1000,0,189.99),
    ("PSU", "be quiet!","Dark Power 13 1000W",    "enthusiast","workstation",0,0,0,0,0,0,1000,0,279.99),
    ("PSU", "EVGA",     "SuperNOVA 750 G6",       "mid-range", "gaming",  0,0,0,0,0,0,750,0,119.99),
    ("PSU", "EVGA",     "SuperNOVA 850 G6",       "high-end",  "gaming",  0,0,0,0,0,0,850,0,139.99),
    ("PSU", "EVGA",     "SuperNOVA 1000 G6",      "enthusiast","gaming",  0,0,0,0,0,0,1000,0,169.99),
    ("PSU", "Corsair",  "HX1200 1200W 80+ Plat",  "enthusiast","workstation",0,0,0,0,0,0,1200,0,229.99),

    # Case
    ("Case", "Lian Li",   "PC-O11 Dynamic",       "mid-range", "gaming",  0,0,0,0,0,0,0,0,139.99),
    ("Case", "Lian Li",   "PC-O11 Dynamic EVO",   "high-end",  "gaming",  0,0,0,0,0,0,0,0,169.99),
    ("Case", "Corsair",   "4000D Airflow",         "mid-range", "gaming",  0,0,0,0,0,0,0,0,94.99),
    ("Case", "Corsair",   "5000D Airflow",         "high-end",  "gaming",  0,0,0,0,0,0,0,0,174.99),
    ("Case", "NZXT",      "H510",                  "budget",    "gaming",  0,0,0,0,0,0,0,0,79.99),
    ("Case", "NZXT",      "H7 Flow",               "high-end",  "gaming",  0,0,0,0,0,0,0,0,149.99),
    ("Case", "Fractal",   "Torrent",               "high-end",  "editing", 0,0,0,0,0,0,0,0,189.99),
    ("Case", "Fractal",   "Define 7",              "high-end",  "workstation",0,0,0,0,0,0,0,0,179.99),
    ("Case", "be quiet!", "Pure Base 500DX",       "mid-range", "gaming",  0,0,0,0,0,0,0,0,109.99),
    ("Case", "Phanteks",  "Enthoo Pro II",         "enthusiast","workstation",0,0,0,0,0,0,0,0,229.99),

    # Cooler
    ("Cooler", "Noctua",       "NH-D15",                  "high-end",  "gaming", 0,0,0,0,0,0,0,0,99.99),
    ("Cooler", "Noctua",       "NH-U12S",                 "mid-range", "gaming", 0,0,0,0,0,0,0,0,74.99),
    ("Cooler", "be quiet!",    "Dark Rock Pro 4",         "high-end",  "gaming", 0,0,0,0,0,0,0,0,89.99),
    ("Cooler", "Cooler Master","Hyper 212",               "budget",    "gaming", 0,0,0,0,0,0,0,0,39.99),
    ("Cooler", "DeepCool",     "AK620",                   "mid-range", "gaming", 0,0,0,0,0,0,0,0,59.99),
    ("Cooler", "Thermalright", "Peerless Assassin 120",   "budget",    "gaming", 0,0,0,0,0,0,0,0,44.99),
    ("Cooler", "Corsair",      "iCUE H150i Elite",        "enthusiast","gaming", 0,0,0,0,0,0,0,0,199.99),
    ("Cooler", "Corsair",      "iCUE H100i Elite",        "high-end",  "gaming", 0,0,0,0,0,0,0,0,149.99),
    ("Cooler", "NZXT",         "Kraken X73",              "enthusiast","gaming", 0,0,0,0,0,0,0,0,179.99),
    ("Cooler", "NZXT",         "Kraken X53",              "high-end",  "gaming", 0,0,0,0,0,0,0,0,129.99),
    ("Cooler", "DeepCool",     "LT720",                   "high-end",  "editing",0,0,0,0,0,0,0,0,149.99),
    ("Cooler", "Lian Li",      "Galahad 360",             "high-end",  "editing",0,0,0,0,0,0,0,0,159.99),
]


def build_training_dataframe() -> pd.DataFrame:
    columns = [
        "category", "brand", "model", "tier", "usage",
        "core_count", "threads", "base_clock_ghz", "vram_gb",
        "ram_size_gb", "storage_gb", "psu_wattage", "tdp_watts", "price_usd"
    ]
    df = pd.DataFrame(COMPONENTS, columns=columns)

    # Augment dataset with noise variations (simulate market spread)
    augmented = []
    rng = np.random.default_rng(42)
    for _, row in df.iterrows():
        for _ in range(8):  # 8 synthetic variations per component
            noise = rng.uniform(0.85, 1.18)
            new_row = row.copy()
            new_row["price_usd"] = round(row["price_usd"] * noise, 2)
            augmented.append(new_row)

    aug_df = pd.DataFrame(augmented, columns=columns)
    full_df = pd.concat([df, aug_df], ignore_index=True)
    return full_df


def encode_features(df: pd.DataFrame) -> tuple:
    """
    Ordinal-encode categorical columns, return (X, y).
    """
    from sklearn.preprocessing import OrdinalEncoder

    cat_cols = ["category", "brand", "tier", "usage"]
    num_cols = ["core_count", "threads", "base_clock_ghz", "vram_gb",
                "ram_size_gb", "storage_gb", "psu_wattage", "tdp_watts"]

    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    cat_encoded = encoder.fit_transform(df[cat_cols])
    num_data = df[num_cols].values

    X = np.hstack([cat_encoded, num_data])
    y = df["price_usd"].values
    return X, y, encoder


def train_and_save():
    logger.info("🔧 Generating synthetic training dataset...")
    df = build_training_dataframe()
    logger.info("   Dataset size: %d records", len(df))

    # Save raw CSV
    df.to_csv(CSV_PATH, index=False)
    logger.info("📁 Raw dataset saved to %s", CSV_PATH)

    logger.info("🔢 Encoding features...")
    X, y, encoder = encode_features(df)

    # Split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)

    logger.info("🤖 Training XGBoost regressor...")
    try:
        from xgboost import XGBRegressor
        model = XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            verbosity=0,
        )
    except ImportError:
        logger.warning("XGBoost not available, falling back to RandomForest...")
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

    model.fit(X_train, y_train)

    # Evaluate
    from sklearn.metrics import mean_absolute_error, r2_score
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    logger.info("📊 Evaluation — MAE: $%.2f | R²: %.4f", mae, r2)

    # Save model + encoder
    import joblib
    joblib.dump(model, MODEL_PATH)
    encoder_path = OUTPUT_DIR / "feature_encoder.pkl"
    joblib.dump(encoder, encoder_path)

    logger.info("✅ Model saved → %s", MODEL_PATH)
    logger.info("✅ Encoder saved → %s", encoder_path)
    return model, encoder, mae, r2


if __name__ == "__main__":
    train_and_save()
    logger.info("🎉 Training complete!")
