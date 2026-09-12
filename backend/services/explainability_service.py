"""NexSolve P8 Explainability & Decision-Support Service.

Generates transparent, auditable decision-support explanation packages.

Safety & Governance Rules:
- 100% strict separation of ML Landslide Risk ($P \\in [0, 1]$) and P7C Vulnerability ($S \\in [0, 100]$).
- Global Random Forest feature importances are explicitly labeled as MODEL-LEVEL FEATURE IMPORTANCE.
- Local feature attribution explicitly sets `local_explanation_available: false` (no unverified SHAP/LIME approximations).
- Weather status (`LIVE`, `STALE`, `HISTORICAL`, `UNAVAILABLE`) is explicitly reported.
- Explicit human verification checklists and conservative uncertainty declarations.
- `is_official_warning` remains strictly `False`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from backend.services.model_loader import load_active_model

# Cache global model feature importances
_ACTIVE_MODEL_IMPORTANCES: Optional[dict[str, float]] = None


def get_model_feature_importances() -> dict[str, float]:
    """Retrieve global feature importances from active trained Random Forest model."""
    global _ACTIVE_MODEL_IMPORTANCES
    if _ACTIVE_MODEL_IMPORTANCES is not None:
        return _ACTIVE_MODEL_IMPORTANCES

    try:
        pkg = load_active_model()
        if pkg and "model" in pkg and hasattr(pkg["model"], "feature_importances_"):
            features = pkg.get("features", [
                "latitude", "longitude", "rainfall_1d", "rainfall_3d", "rainfall_7d", "month_sin", "month_cos"
            ])
            importances = pkg["model"].feature_importances_
            _ACTIVE_MODEL_IMPORTANCES = {
                feat: round(float(imp), 4)
                for feat, imp in zip(features, importances)
            }
            return _ACTIVE_MODEL_IMPORTANCES
    except Exception as exc:
        print(f"Warning: Unable to load model feature importances: {exc}")

    # Fallback static importance dictionary matching trained candidate_a_rf_v1
    return {
        "rainfall_1d": 0.2334,
        "rainfall_3d": 0.2291,
        "rainfall_7d": 0.2251,
        "longitude": 0.0980,
        "latitude": 0.0894,
        "month_cos": 0.0824,
        "month_sin": 0.0426,
    }


def generate_explainability_report(
    risk_decision: dict[str, Any] | Any,
    weather_data: Optional[dict[str, Any]] = None,
    features: Optional[dict[str, Any]] = None,
    vulnerability_profile: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Generate structured P8 explainability & decision-support report."""
    # Handle dataclass or dict for risk_decision
    if hasattr(risk_decision, "to_dict"):
        rd = risk_decision.to_dict()
    elif isinstance(risk_decision, dict):
        rd = risk_decision
    else:
        rd = {}

    risk_probability = rd.get("riskProbability", rd.get("risk_probability"))
    risk_level = rd.get("riskLevel", rd.get("risk_level", "DATA_UNAVAILABLE"))
    confidence = rd.get("confidence", "UNAVAILABLE")
    model_id = rd.get("modelId", rd.get("model_id", "candidate_a_rf_v1"))
    model_version = rd.get("modelVersion", rd.get("model_version", "1.1.0"))
    feature_schema_version = rd.get("featureSchemaVersion", rd.get("feature_schema_version", "v1"))

    # 1. Weather Provenance & Status
    w_info = weather_data or {}
    w_avail = w_info.get("available", False) or w_info.get("weather_available", False)
    if not w_avail or (w_info.get("rainfall_1d") is None and w_info.get("rainfall_24h") is None):
        weather_status = "UNAVAILABLE"
    elif w_info.get("quality") == "stale" or (w_info.get("data_age_hours") is not None and w_info.get("data_age_hours") > 3.0):
        weather_status = "STALE"
    elif w_info.get("is_live") is False:
        weather_status = "HISTORICAL"
    else:
        weather_status = "LIVE"

    weather_source = w_info.get("source", "Open-Meteo API / IMD Station Feed" if w_avail else "Weather Feed Unavailable")
    weather_timestamp = w_info.get("timestamp")

    r1d = w_info.get("rainfall_1d") if w_info.get("rainfall_1d") is not None else w_info.get("rainfall_24h")
    r3d = w_info.get("rainfall_3d")
    r7d = w_info.get("rainfall_7d")

    # 2. Feature Values
    feat_dict = features or {}
    feature_values = {
        "latitude": feat_dict.get("latitude"),
        "longitude": feat_dict.get("longitude"),
        "rainfall_1d": r1d if r1d is not None else feat_dict.get("rainfall_1d"),
        "rainfall_3d": r3d if r3d is not None else feat_dict.get("rainfall_3d"),
        "rainfall_7d": r7d if r7d is not None else feat_dict.get("rainfall_7d"),
        "month_sin": feat_dict.get("month_sin"),
        "month_cos": feat_dict.get("month_cos"),
    }

    # 3. Model-Level Feature Importance (Global)
    model_importances = get_model_feature_importances()

    # 4. Local Explanation Declaration
    local_explanation = {
        "local_explanation_available": False,
        "rationale": "Conservative decision support policy — Local feature attribution (e.g., SHAP/LIME) is not calculated to avoid generating unverified approximation values without model retraining.",
        "note": "Rainfall-related features and seasonal patterns contributed to the model's estimated risk.",
    }

    # 5. Contributing Factors & Explanation Text
    reason_codes = rd.get("reasonCodes", rd.get("reason_codes", []))
    contributing_factors = []

    if r1d is not None:
        contributing_factors.append({
            "feature": "24h Rainfall",
            "value_display": f"{r1d:.1f} mm",
            "global_importance": model_importances.get("rainfall_1d", 0.2334),
            "description": "Short-term antecedent precipitation triggering potential slope instability.",
        })
    if r3d is not None:
        contributing_factors.append({
            "feature": "3-Day Rainfall Accumulation",
            "value_display": f"{r3d:.1f} mm",
            "global_importance": model_importances.get("rainfall_3d", 0.2291),
            "description": "Medium-term soil saturation accumulation.",
        })
    if r7d is not None:
        contributing_factors.append({
            "feature": "7-Day Rainfall Accumulation",
            "value_display": f"{r7d:.1f} mm",
            "global_importance": model_importances.get("rainfall_7d", 0.2251),
            "description": "Long-term cumulative rainfall weakening hill slope shear strength.",
        })

    # Conservative, non-causal explanation text
    if risk_level == "RED":
        explanation_text = "Heavy rainfall accumulation and seasonal monsoon factors contributed to the model's high landslide hazard estimate."
    elif risk_level in ("ORANGE", "YELLOW"):
        explanation_text = "Moderate antecedent rainfall and terrain location features contributed to the model's elevated risk estimate."
    elif risk_level == "GREEN":
        explanation_text = "Low rainfall accumulation and background seasonal baseline contributed to the model's low landslide hazard estimate."
    else:
        explanation_text = "Landslide hazard evaluation is currently unavailable because required live weather data could not be verified."

    # 6. Uncertainty Section
    if weather_status in ("UNAVAILABLE", "STALE"):
        uncertainty_level = "HIGH"
    elif risk_level in ("RED", "ORANGE"):
        uncertainty_level = "MEDIUM"
    else:
        uncertainty_level = "LOW"

    uncertainty = {
        "uncertainty_level": uncertainty_level,
        "uncertainty_notes": [
            "Temporal validation performance varies across rolling historical holdout periods.",
            "Historical controls reflect paired historical landslide controls, not unconstrained negative samples.",
            "District/state evaluation coverage is incomplete across 115 NER districts.",
            "Real-time soil saturation and high-resolution DEM slope layers are pending sensor deployment.",
        ],
        "data_limitations": (
            "Weather observation feed quality: "
            f"{'LIVE' if weather_status == 'LIVE' else 'UNVERIFIED / STALE' if weather_status == 'STALE' else 'UNAVAILABLE'}. "
            "Microclimate rainfall variations in steep mountain valleys may differ from regional weather grid cells."
        ),
        "model_limitations": (
            "Model predictions represent statistical hazard probability based on historical training data. "
            "Does NOT guarantee site-specific ground slope movement or exact failure timing."
        ),
    }

    # 7. Human Verification Items (Human-in-the-Loop Checklist)
    human_verification_items = [
        {
            "item_id": "VERIFY_RAINFALL",
            "label": "Verify Local Weather Observations",
            "description": "Confirm rainfall accumulation with nearest IMD/AWS automated weather station or rain gauge.",
            "category": "Weather Data",
        },
        {
            "item_id": "CHECK_FIELD_REPORTS",
            "label": "Review Field Reports & Ground Observations",
            "description": "Inspect recent crowd-sourced observations or field report submissions for signs of tension cracks or rockfall.",
            "category": "Ground Inspection",
        },
        {
            "item_id": "VERIFY_CORRIDOR_EXPOSURE",
            "label": "Inspect Highway Corridor & Settlement Exposure",
            "description": "Cross-reference arterial corridor status (e.g. NH-306, NH-2) and critical infrastructure assets along slope cuts.",
            "category": "Infrastructure",
        },
        {
            "item_id": "CONFIRM_AUTHORITY",
            "label": "Consult Authorized Disaster Management Personnel",
            "description": "Escalate findings to SDMA/NDMA officials prior to issuing operational public advisories.",
            "category": "Protocol",
        },
    ]

    # 8. Exposure & Vulnerability Context (P7C Decoupled Layer)
    vuln_info = vulnerability_profile or {}
    vuln_score = vuln_info.get("composite_vulnerability_score")
    vuln_status = vuln_info.get("status", "INSUFFICIENT_DATA")
    vuln_completeness = vuln_info.get("data_completeness_pct", 0.0)
    vuln_confidence = vuln_info.get("confidence", "UNAVAILABLE")

    if vuln_score is not None:
        vuln_display = f"Prototype Vulnerability Score: {vuln_score}/100 (Decoupled from ML Risk)"
    else:
        vuln_display = "VULNERABILITY DATA INSUFFICIENT"

    vulnerability_context = {
        "status": vuln_status,
        "confidence": vuln_confidence,
        "data_completeness_pct": vuln_completeness,
        "composite_vulnerability_score": vuln_score,
        "display_message": vuln_display,
        "contributing_factors": vuln_info.get("contributing_factors", []),
        "decoupling_rule": "Landslide ML risk indicates modeled hazard likelihood. Exposure/vulnerability indicates historical asset exposure. They are strictly separate decision layers and NEVER multiplied or merged.",
    }

    return {
        "risk_probability": risk_probability,
        "risk_level": risk_level,
        "confidence": confidence,
        "model_version": model_version,
        "model_id": model_id,
        "feature_schema_version": feature_schema_version,
        "weather_status": weather_status,
        "weather_source": weather_source,
        "weather_timestamp": weather_timestamp,
        "feature_values": feature_values,
        "model_feature_importance": model_importances,
        "local_explanation": local_explanation,
        "contributing_factors": contributing_factors,
        "reason_codes": reason_codes,
        "explanation_text": explanation_text,
        "uncertainty": uncertainty,
        "recommended_action": rd.get("recommendedAction", rd.get("recommended_action", "Verify local ground conditions.")),
        "human_verification_items": human_verification_items,
        "vulnerability_context": vulnerability_context,
        "is_official_warning": False,
        "disclaimer": "NexSolve Prototype Decision Support System — Information for internal decision-support assessment only. Not an official government emergency warning. Authorized human judgment and field verification are required.",
    }
