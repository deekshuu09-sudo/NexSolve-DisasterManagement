# NexSolve P8 Explainability & Decision-Support Layer Audit Report

**Generated Date**: 2026-09-12  
**Framework Version**: `1.0.0-PROTOTYPE`  
**Active Production Model**: Candidate A (`candidate_a_rf_v1.pkl`, Version 1.1.0)  
**Status**: **COMPLETE & VERIFIED**  

---

## Executive Summary

Phase 8 (P8) implements a transparent, auditable decision-support explainability layer (`backend/services/explainability_service.py`) for the active Candidate A model. The system provides decision-support explanations, weather feed quality provenance, model-level feature importance attribution, explicit uncertainty declarations, and human verification checklists—while strictly enforcing 100% separation between ML Landslide Hazard Risk ($P \in [0, 1]$) and P7C Exposure/Vulnerability Scores ($S \in [0, 100]$).

---

## 1. Files Created & Modified

1. **`backend/services/explainability_service.py` [NEW]**:
   - Central explainability engine producing structured explanation reports.
   - Extracts global Random Forest feature importances (`MODEL-LEVEL FEATURE IMPORTANCE`).
   - Conservative local attribution policy: explicitly declares `local_explanation_available: false` with rationale to prevent fabricating unverified SHAP values.
   - Formulates non-causal natural language explanations.
   - Generates human verification checklists and uncertainty notes.

2. **`backend/main.py` [MODIFY]**:
   - Enriched `POST /api/risk` endpoint to include nested `explainability` payload.
   - Added dedicated endpoint `GET /api/explainability/{district_id}`.

3. **`frontend/src/lib/api.ts` [MODIFY]**:
   - Added `ExplainabilityReport`, `UncertaintySection`, and `HumanVerificationItem` TypeScript interfaces.
   - Added `getExplainability(districtId)` helper function.

4. **`frontend/src/App.tsx` [MODIFY]**:
   - Updated decision support dashboard card with dedicated P8 Explainability sections:
     - **LANDSLIDE RISK**: Probability, Risk level, Confidence.
     - **WHY THIS RESULT?**: Model-level feature importances, rainfall factors, non-causal explanation text.
     - **DATA QUALITY**: Live / Stale / Unavailable weather status, timestamp, source.
     - **EXPOSURE & VULNERABILITY**: Visually separate card displaying P7C score or `VULNERABILITY DATA INSUFFICIENT`.
     - **DECISION SUPPORT & HUMAN VERIFICATION**: Recommended authority action & interactive human verification checklist.
     - **DISCLAIMER**: Prototype decision-support notice.

5. **`backend/test_p8_explainability.py` [NEW]**:
   - Comprehensive unit test suite validating 15 test scenarios.

---

## 2. API Contract Extensions

### `POST /api/risk`
```json
{
  "success": true,
  "data": {
    "riskScore": 45.0,
    "status": "Moderate",
    "severity": "Moderate",
    "confidence": 45.0,
    "factors": [...],
    "modelSource": "NexSolve leakage-free RF",
    "modelVersion": "1.1.0",
    "modelId": "candidate_a_rf_v1",
    "featureSchemaVersion": "v1",
    "decision": { ... },
    "explainability": {
      "risk_probability": 0.45,
      "risk_level": "YELLOW",
      "confidence": "HIGH",
      "model_version": "1.1.0",
      "model_id": "candidate_a_rf_v1",
      "feature_schema_version": "v1",
      "weather_status": "LIVE",
      "weather_source": "Open-Meteo API / IMD Station Feed",
      "weather_timestamp": "2026-09-12T11:20:00Z",
      "feature_values": { "latitude": 23.4756, "longitude": 93.3289, "rainfall_1d": 25.0, "rainfall_3d": 45.0, "rainfall_7d": 70.0 },
      "model_feature_importance": { "rainfall_1d": 0.2334, "rainfall_3d": 0.2291, "rainfall_7d": 0.2251, "longitude": 0.098, "latitude": 0.0894, "month_cos": 0.0824, "month_sin": 0.0426 },
      "local_explanation": {
        "local_explanation_available": false,
        "rationale": "Conservative decision support policy — Local feature attribution (e.g., SHAP/LIME) is not calculated to avoid generating unverified approximation values without model retraining.",
        "note": "Rainfall-related features and seasonal patterns contributed to the model's estimated risk."
      },
      "contributing_factors": [...],
      "reason_codes": ["WEATHER_FEED_LIVE", "RAIN_1D_ELEVATED"],
      "explanation_text": "Moderate antecedent rainfall and terrain location features contributed to the model's elevated risk estimate.",
      "uncertainty": {
        "uncertainty_level": "LOW",
        "uncertainty_notes": [...],
        "data_limitations": "Weather observation feed quality: LIVE. Microclimate rainfall variations in steep mountain valleys may differ from regional weather grid cells.",
        "model_limitations": "Model predictions represent statistical hazard probability based on historical training data. Does NOT guarantee site-specific ground slope movement or exact failure timing."
      },
      "recommended_action": "Issue local hazard monitoring advisory for vulnerable slopes and monitored road corridors.",
      "human_verification_items": [...],
      "vulnerability_context": { ... },
      "is_official_warning": false,
      "disclaimer": "NexSolve Prototype Decision Support System — Information for internal decision-support assessment only. Not an official government emergency warning. Authorized human judgment and field verification are required."
    }
  }
}
```

### `GET /api/explainability/{district_id}`
Returns complete district risk prediction, weather feed provenance, P7C vulnerability intelligence, and P8 structured explainability report.

---

## 3. Explanation Methodology & Safety Rules

1. **Non-Causal Feature Importance Wording**:
   - Feature importances are explicitly labeled as `MODEL-LEVEL FEATURE IMPORTANCE`.
   - Explanations state *"Rainfall-related features contributed to the model's estimated risk"* rather than claiming direct physical causality.

2. **Conservative Local Attribution Policy**:
   - Explicitly returns `local_explanation_available: false`.
   - Rationale: Avoids generating unverified SHAP/LIME approximations without retraining.

3. **Weather Provenance & Gating**:
   - Weather statuses (`LIVE`, `STALE`, `HISTORICAL`, `UNAVAILABLE`) are explicitly tracked.
   - If weather data is unavailable, `risk_probability` remains strictly `null` (`DATA_UNAVAILABLE`, `NOT_EVALUABLE`), adhering strictly to P6 safety gating.

4. **100% Decoupled Vulnerability Layer**:
   - P7C Exposure/Vulnerability Scores ($S \in [0, 100]$) are displayed in a visually distinct panel.
   - Risk $\times$ Vulnerability is **NEVER** calculated or merged.
   - Missing vulnerability data displays `VULNERABILITY DATA INSUFFICIENT` without interpreting absence as low vulnerability.

5. **Human-in-the-Loop & Non-Official Warning Authority**:
   - `human_verification_items` provides a 4-point verification checklist (Verify rainfall, inspect field reports, check corridor exposure, confirm with SDMA/NDMA).
   - `is_official_warning` remains strictly `false`. No automatic evacuation orders are issued.

---

## 4. Verification Results

| Metric / Check | Value / Status | Verification Method |
|---|---|---|
| Backend Unit Tests Passed | **127 / 127 (100%)** | `python3 -m unittest discover` |
| Frontend Build Status | **PASS (0 Errors)** | `npm run build` |
| Original Model SHA-256 | `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1` | `shasum -a 256` (**MATCHED**) |
| Candidate A Model SHA-256 | `1acad34e85b53df0cb68e5e81cd81d68066c4173792e65a51288b35557ba0f72` | `shasum -a 256` (**MATCHED**) |
| P6 Risk Decision Thresholds | Elevated: `0.35`, Warning: `0.50`, Emergency: `0.75` | `risk_policy.json` (**UNTOUCHED**) |

---

## 5. Final Sign-off

**PHASE 8 EXPLAINABILITY & DECISION-SUPPORT LAYER IS COMPLETE, VALIDATED, AND LOCKED.**
