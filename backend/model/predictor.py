"""Landslide risk prediction service.

Uses the trained Random Forest model when all required ML features
are available. Falls back to the transparent baseline when they are not.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from datetime import datetime
import math
import pickle
import pandas as pd

# ============================================================
# TRAINED MODEL
# ============================================================

MODEL_PATH = Path(__file__).parent / "landslide_model.pkl"


@dataclass
class Prediction:
    score: float
    status: str
    confidence: float
    factors: list[dict[str, Any]]
    model_source: str


def _clamp(
    value: float,
    low: float = 0.0,
    high: float = 100.0
) -> float:
    return max(low, min(high, value))


# ============================================================
# BASELINE FALLBACK
# ============================================================

def baseline_predict(
    features: dict[str, float]
) -> Prediction:

    rainfall = _clamp(
        features.get("rain24h", 0) / 2.0
    )

    soil = _clamp(
        features.get("soilSat", 0)
    )

    slope = _clamp(
        features.get("slopeAngle", 0) / 45.0 * 100
    )

    history = _clamp(
        features.get("gsiEvents", 0) / 20.0 * 100
    )

    score = (
        0.40 * rainfall
        + 0.25 * soil
        + 0.20 * slope
        + 0.15 * history
    )

    score = round(
        _clamp(score),
        1
    )

    if score >= 80:
        status = "Critical"
    elif score >= 60:
        status = "High"
    elif score >= 40:
        status = "Moderate"
    else:
        status = "Low"

    factors = [
        {
            "name": "Rainfall Intensity & Accumulation",
            "weight": 40,
            "impact": round(rainfall, 1)
        },
        {
            "name": "Soil Moisture Saturation",
            "weight": 25,
            "impact": round(soil, 1)
        },
        {
            "name": "Terrain Slope & DEM Cut Angle",
            "weight": 20,
            "impact": round(slope, 1)
        },
        {
            "name": "GSI Historical Inventory",
            "weight": 15,
            "impact": round(history, 1)
        },
    ]

    return Prediction(
        score,
        status,
        62.0,
        factors,
        "transparent-baseline"
    )


# ============================================================
# LOAD TRAINED MODEL
# ============================================================

def _load_model():

    if not MODEL_PATH.exists():
        return None

    try:
        with open(MODEL_PATH, "rb") as f:
            package = pickle.load(f)

        return package

    except Exception as exc:
        print(
            f"Warning: unable to load trained model: {exc}"
        )
        return None


MODEL_PACKAGE = _load_model()


# ============================================================
# ML PREDICTION
# ============================================================

def ml_predict(
    features: dict[str, float]
) -> Prediction | None:

    if MODEL_PACKAGE is None:
        return None

    model = MODEL_PACKAGE["model"]

    required = [
        "latitude",
        "longitude",
        "rainfall_1d",
        "rainfall_3d",
        "rainfall_7d",
    ]

    # We need all rainfall/location values
    # for the trained model.
    if not all(
        key in features
        and features[key] is not None
        for key in required
    ):
        return None

    try:

        latitude = float(
            features["latitude"]
        )

        longitude = float(
            features["longitude"]
        )

        rainfall_1d = float(
            features["rainfall_1d"]
        )

        rainfall_3d = float(
            features["rainfall_3d"]
        )

        rainfall_7d = float(
            features["rainfall_7d"]
        )

        # ----------------------------------------------------
        # Date / seasonal features
        # ----------------------------------------------------

        date_value = features.get("date")

        if date_value is None:

            month = datetime.now().month

        elif isinstance(date_value, str):

            month = datetime.fromisoformat(
                date_value
            ).month

        else:

            month = int(date_value)

        month_sin = math.sin(
            2 * math.pi * month / 12
        )

        month_cos = math.cos(
            2 * math.pi * month / 12
        )

        # ----------------------------------------------------
        # Model input
        # ----------------------------------------------------

        X = pd.DataFrame([{
            "latitude": latitude,
            "longitude": longitude,
            "rainfall_1d": rainfall_1d,
            "rainfall_3d": rainfall_3d,
            "rainfall_7d": rainfall_7d,
            "month_sin": month_sin,
            "month_cos": month_cos,
        }])

        probability = float(
            model.predict_proba(X)[0][1]
        )

        score = round(
            _clamp(probability * 100),
            1
        )

        # ----------------------------------------------------
        # Risk category
        # ----------------------------------------------------

        if score >= 80:
            status = "Critical"

        elif score >= 60:
            status = "High"

        elif score >= 40:
            status = "Moderate"

        else:
            status = "Low"

        # ----------------------------------------------------
        # Explainable rainfall factors
        # ----------------------------------------------------

        max_rain = max(
            rainfall_1d,
            rainfall_3d / 3,
            rainfall_7d / 7,
            1
        )

        rainfall_1d_impact = _clamp(
            rainfall_1d / max_rain * 100
        )

        rainfall_3d_impact = _clamp(
            (rainfall_3d / 3)
            / max_rain
            * 100
        )

        rainfall_7d_impact = _clamp(
            (rainfall_7d / 7)
            / max_rain
            * 100
        )

        factors = [
            {
                "name": "24h Rainfall",
                "weight": 24,
                "impact": round(
                    rainfall_1d_impact,
                    1
                )
            },
            {
                "name": "3-Day Rainfall Accumulation",
                "weight": 23,
                "impact": round(
                    rainfall_3d_impact,
                    1
                )
            },
            {
                "name": "7-Day Rainfall Accumulation",
                "weight": 19,
                "impact": round(
                    rainfall_7d_impact,
                    1
                )
            },
            {
                "name": "Seasonal Pattern",
                "weight": 16,
                "impact": round(
                    abs(month_cos) * 100,
                    1
                )
            },
            {
                "name": "Location",
                "weight": 18,
                "impact": 50.0
            },
        ]

        return Prediction(
            score=score,
            status=status,
            confidence=round(
                probability * 100,
                1
            ),
            factors=factors,
            model_source="trained-random-forest"
        )

    except Exception as exc:

        print(
            f"ML prediction failed: {exc}"
        )

        return None


# ============================================================
# PUBLIC PREDICTION FUNCTION
# ============================================================

def predict(
    features: dict[str, float]
) -> Prediction:

    prediction = ml_predict(features)

    if prediction is not None:
        return prediction

    return baseline_predict(features)