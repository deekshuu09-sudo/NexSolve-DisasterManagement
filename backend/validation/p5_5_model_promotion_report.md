# P5.5 Controlled Model Promotion Report

## Previous Production Model
- **Artifact Path**: `backend/model/landslide_model.pkl`
- **Legacy Version**: `1.0.0` (`RF-PROD-LEGACY-BASELINE`)
- **Status**: Archived and Preserved under `backend/model/archive/landslide_model_v_current.pkl`.

## Previous Production SHA-256
- **SHA-256 Hash**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1` (**100% VERIFIED & UNCHANGED**)

## Promoted Model
- **Candidate ID**: `candidate_a_rf_v1`
- **Model Label**: `RF-LEAKAGE-FREE-BASELINE`
- **Model Version**: `1.1.0`
- **Model Type**: `RandomForestClassifier` (300 trees, `max_depth=12`, `class_weight='balanced'`, `random_state=42`)
- **Training Period**: `date <= 2023-12-31` (490 samples) — Leakage-Free
- **Locked Holdout Validation (2024–2025)**: ROC-AUC = **0.9206**, PR-AUC = **0.9328**, F1 = **0.8258**.

## Promoted Model SHA-256
- **SHA-256 Hash**: `1acad34e85b53df0cb68e5e81cd81d68066c4173792e65a51288b35557ba0f72`

## Feature Contract
Candidate A uses strictly the 7 production features in exact schema order:
1. `latitude`
2. `longitude`
3. `rainfall_1d`
4. `rainfall_3d`
5. `rainfall_7d`
6. `month_sin`
7. `month_cos`

*Safety Check*: `distance_to_nearest_event_km`, `soilSat`, terrain, and inventory features are strictly excluded from Candidate A prediction inputs.

## Model Registry
Recorded in `backend/model/model_registry.json`. Central loader `backend/services/model_loader.py` dynamically resolves the `ACTIVE` entry via registry metadata.

## Rollback Artifact
- **Rollback Target Path**: `backend/model/archive/landslide_model_v_current.pkl`
- **Verified SHA-256**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`
- **Rollback Mechanism**: 1-step atomic update setting `previous_production_model_v0` to `ACTIVE` in `model_registry.json` via `rollback_to_previous_model()` service method. No retraining required.

## API Changes
- Endpoint `POST /api/risk` exposes model metadata in data payload:
  - `modelVersion`: `"1.1.0"`
  - `modelId`: `"candidate_a_rf_v1"`
  - `modelSource`: `"NexSolve leakage-free RF"`
  - `featureSchemaVersion`: `"v1"`
- Existing frontend response fields (`riskScore`, `status`, `confidence`, `factors`, `weatherStatus`, `terrain`) remain 100% compatible.

## Regression Tests
59 backend unit tests verified:
- Active model registry loading & SHA-256 verification
- Feature schema contract matching
- Missing/unavailable weather feed safety handling
- Rollback artifact verification
- API prediction response compatibility

## Frontend Compatibility
- `npm run build` executed cleanly in `frontend/` with **0 errors**.

## Safety Checks
- Zero synthetic geometry or fabricated environmental data.
- Controls remain designated as `CONTROL / NON-EVENT OBSERVATIONS`.
- Model output presented as `LANDSLIDE RISK / MODEL-ESTIMATED RISK` (non-deterministic).
- Prototype risk bands do NOT claim official government alert certification.

## Final Status
**COMPLETE — PROMOTED TO ACTIVE STATUS**
