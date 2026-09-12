"""NexSolve Central Risk & Alert Decision Engine.

Operational risk-decision layer built on top of model predictions and weather feed health.
Evaluates internal decision-support risk levels, confidence, reason codes, and authority recommendations.
Does NOT issue public evacuation orders or claim government warning authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Optional
import uuid

POLICY_PATH = Path(__file__).resolve().parents[1] / "data" / "config" / "risk_policy.json"


def load_risk_policy() -> dict[str, Any]:
    """Load central risk decision policy configuration."""
    if POLICY_PATH.exists():
        try:
            with open(POLICY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "policy_version": "1.0.0-PROTOTYPE",
        "status": "PROTOTYPE / INTERNAL",
        "thresholds": {
            "candidate_internal_threshold": 0.35,
            "default_comparison_threshold": 0.50,
            "elevated_risk_threshold": 0.35,
            "warning_risk_threshold": 0.50,
            "emergency_risk_threshold": 0.75,
            "rainfall_24h_elevated_mm": 50.0,
            "rainfall_3d_elevated_mm": 100.0,
            "rainfall_7d_elevated_mm": 200.0,
        },
        "rationale": "P5.3.2 candidate threshold operating point configuration.",
        "disclaimer": "NexSolve Internal Decision Support — Thresholds are prototype internal markers.",
    }


POLICY_CONFIG = load_risk_policy()


@dataclass
class RiskDecision:
    alert_id: str
    timestamp: str
    state: str
    district: str
    latitude: float
    longitude: float
    risk_probability: Optional[float]
    risk_level: str
    risk_label: str
    confidence: str
    data_status: str
    decision_status: str
    recommended_action: str
    reason_codes: list[str]
    explanation: str
    model_id: str
    model_version: str
    feature_schema_version: str
    policy_version: str
    is_official_warning: bool = False
    disclaimer: str = (
        "NexSolve Internal Decision Support — Requires Authorized Personnel Assessment"
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert decision to camelCase dictionary for API compatibility."""
        return {
            "alertId": self.alert_id,
            "timestamp": self.timestamp,
            "state": self.state,
            "district": self.district,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "riskProbability": self.risk_probability,
            "riskLevel": self.risk_level,
            "riskLabel": self.risk_label,
            "confidence": self.confidence,
            "dataStatus": self.data_status,
            "decisionStatus": self.decision_status,
            "recommendedAction": self.recommended_action,
            "reasonCodes": self.reason_codes,
            "explanation": self.explanation,
            "modelId": self.model_id,
            "modelVersion": self.model_version,
            "featureSchemaVersion": self.feature_schema_version,
            "policyVersion": self.policy_version,
            "isOfficialWarning": self.is_official_warning,
            "disclaimer": self.disclaimer,
        }


def evaluate_risk_decision(
    model_prediction: Any = None,
    weather_data: Optional[dict[str, Any]] = None,
    location: Optional[dict[str, Any]] = None,
    timestamp: Optional[str] = None,
    extra_context: Optional[dict[str, Any]] = None,
) -> RiskDecision:
    """Evaluate operational risk decision layer for given model prediction and weather context.

    P0 Safety Rule: If live weather data is unavailable or missing required fields,
    returns risk_probability = null, risk_level = "DATA_UNAVAILABLE", and decision_status = "NOT_EVALUABLE".
    """
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    policy = load_risk_policy()
    policy_ver = policy.get("policy_version", "1.0.0-PROTOTYPE")
    thresholds = policy.get("thresholds", {})

    loc = location or {}
    state = loc.get("state", "NER Region")
    district = loc.get("district", loc.get("name", "Monitored Point"))
    lat = float(loc.get("latitude", loc.get("lat", 0.0)))
    lng = float(loc.get("longitude", loc.get("lng", 0.0)))

    alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"

    # Extract model metadata defaults
    model_id = "candidate_a_rf_v1"
    model_version = "1.1.0"
    feature_schema_version = "v1"

    if model_prediction is not None:
        model_id = getattr(model_prediction, "model_id", getattr(model_prediction, "modelId", model_id))
        model_version = getattr(model_prediction, "model_version", getattr(model_prediction, "modelVersion", model_version))
        feature_schema_version = getattr(model_prediction, "feature_schema_version", getattr(model_prediction, "featureSchemaVersion", feature_schema_version))
        if isinstance(model_prediction, dict):
            model_id = model_prediction.get("model_id", model_prediction.get("modelId", model_id))
            model_version = model_prediction.get("model_version", model_prediction.get("modelVersion", model_version))
            feature_schema_version = model_prediction.get("feature_schema_version", model_prediction.get("featureSchemaVersion", feature_schema_version))

    # DATA AVAILABILITY GATING (P0 SAFETY RULE)
    w_avail = False
    if weather_data and isinstance(weather_data, dict):
        w_avail = weather_data.get("available", False)
        if weather_data.get("rainfall_1d") is None and weather_data.get("rainfall_24h") is None:
            w_avail = False

    if not w_avail:
        return RiskDecision(
            alert_id=alert_id,
            timestamp=ts,
            state=state,
            district=district,
            latitude=lat,
            longitude=lng,
            risk_probability=None,
            risk_level="DATA_UNAVAILABLE",
            risk_label="Data Unavailable",
            confidence="UNAVAILABLE",
            data_status="UNAVAILABLE",
            decision_status="NOT_EVALUABLE",
            recommended_action="Verify local weather station feed and field sensors.",
            reason_codes=["WEATHER_FEED_UNAVAILABLE", "INSUFFICIENT_DATA"],
            explanation="Risk assessment is currently unavailable because required live weather data could not be verified.",
            model_id=model_id,
            model_version=model_version,
            feature_schema_version=feature_schema_version,
            policy_version=policy_ver,
        )

    # Weather is available -> Check weather quality
    is_live = weather_data.get("is_live", True)
    quality = weather_data.get("quality", "good")
    data_age = weather_data.get("data_age_hours", 0)

    reason_codes: list[str] = []

    if is_live and quality == "good" and (data_age is None or data_age <= 3.0):
        reason_codes.append("WEATHER_FEED_LIVE")
        data_status = "VERIFIED_LIVE"
        confidence = "HIGH"
    elif quality == "stale" or (data_age is not None and data_age > 3.0):
        reason_codes.append("WEATHER_FEED_STALE")
        data_status = "STALE"
        confidence = "MEDIUM"
    else:
        reason_codes.append("WEATHER_FEED_LIVE")
        data_status = "VERIFIED_LIVE"
        confidence = "HIGH"

    # Evaluate rainfall thresholds
    r1d = float(weather_data.get("rainfall_1d") or weather_data.get("rainfall_24h") or 0.0)
    r3d = float(weather_data.get("rainfall_3d") or 0.0)
    r7d = float(weather_data.get("rainfall_7d") or 0.0)

    if r1d >= thresholds.get("rainfall_24h_elevated_mm", 50.0):
        reason_codes.append("RAIN_1D_ELEVATED")
    if r3d >= thresholds.get("rainfall_3d_elevated_mm", 100.0):
        reason_codes.append("RAIN_3D_ELEVATED")
    if r7d >= thresholds.get("rainfall_7d_elevated_mm", 200.0):
        reason_codes.append("RAIN_7D_ELEVATED")

    # Evaluate seasonality reason code
    month = datetime.now(timezone.utc).month
    if extra_context and "date" in extra_context:
        try:
            month = datetime.fromisoformat(str(extra_context["date"])).month
        except Exception:
            pass
    if 5 <= month <= 9:
        reason_codes.append("SEASONAL_FACTOR")

    # Evaluate model probability
    prob: float = 0.0
    if model_prediction is not None:
        if hasattr(model_prediction, "score"):
            prob = float(model_prediction.score) / 100.0
        elif isinstance(model_prediction, dict) and "score" in model_prediction:
            prob = float(model_prediction["score"]) / 100.0
        elif isinstance(model_prediction, dict) and "riskScore" in model_prediction:
            prob = float(model_prediction["riskScore"]) / 100.0
        elif isinstance(model_prediction, (float, int)):
            prob = float(model_prediction)
            if prob > 1.0:
                prob = prob / 100.0

    prob = round(max(0.0, min(1.0, prob)), 4)

    # Determine risk level based on configured thresholds
    elevated_t = thresholds.get("elevated_risk_threshold", 0.35)
    warning_t = thresholds.get("warning_risk_threshold", 0.50)
    emergency_t = thresholds.get("emergency_risk_threshold", 0.75)

    if prob >= emergency_t:
        risk_level = "RED"
        risk_label = "Emergency Support"
        recommended_action = (
            "Escalate to authorized disaster-management personnel for immediate assessment."
        )
        explanation = (
            "Critical landslide risk is estimated based on heavy rainfall accumulation and the model's risk score. "
            "This is decision-support information and requires immediate field verification by authorized personnel."
        )
        reason_codes.append("MODEL_HIGH_RISK")
    elif prob >= warning_t:
        risk_level = "ORANGE"
        risk_label = "Warning"
        recommended_action = (
            "Prepare response resources and verify field conditions."
        )
        explanation = (
            "Elevated landslide risk is estimated based on recent rainfall conditions and the model's risk score. "
            "This is decision-support information and requires authority review."
        )
        reason_codes.append("MODEL_ELEVATED_RISK")
    elif prob >= elevated_t:
        risk_level = "YELLOW"
        risk_label = "Watch"
        recommended_action = (
            "Increase monitoring and review local conditions."
        )
        explanation = (
            "Moderate landslide watch status estimated based on weather observations and model probability score. "
            "Increase monitoring of local terrain and arterial roads."
        )
        reason_codes.append("MODEL_ELEVATED_RISK")
    else:
        risk_level = "GREEN"
        risk_label = "Normal Risk"
        recommended_action = (
            "Continue routine monitoring."
        )
        explanation = (
            "Normal landslide risk estimated based on current weather observations. Continue routine monitoring."
        )
        reason_codes.append("MODEL_LOW_RISK")

    return RiskDecision(
        alert_id=alert_id,
        timestamp=ts,
        state=state,
        district=district,
        latitude=lat,
        longitude=lng,
        risk_probability=prob,
        risk_level=risk_level,
        risk_label=risk_label,
        confidence=confidence,
        data_status=data_status,
        decision_status="EVALUATED",
        recommended_action=recommended_action,
        reason_codes=reason_codes,
        explanation=explanation,
        model_id=model_id,
        model_version=model_version,
        feature_schema_version=feature_schema_version,
        policy_version=policy_ver,
    )
