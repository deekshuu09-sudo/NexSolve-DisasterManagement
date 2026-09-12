# NexSolve — SIH Verified Claims & Limitations Boundary

This document outlines the strict boundary between **empirically verified capabilities** and **known prototype limitations** for the NexSolve Disaster Management System.

---

## 1. Verified System Capabilities (What NexSolve DOES)

| Area | Verified Capability | Evidence / Artifact |
| :--- | :--- | :--- |
| **Spatial Boundary** | Covers 8 Northeastern States within a 131-district official administrative framework. | Survey of India ABDB GeoJSON files (`ner_states_soi.geojson`, `ner_districts_soi.geojson`). |
| **Historical Baseline** | Incorporates 10,492 Geological Survey of India (GSI) landslide inventory events. | Integrated baseline training data. |
| **Terrain Intelligence** | Derived elevation, slope, aspect, and curvature metrics for all 131 districts. | USGS / AWS Open Data Elevation Archive (NASADEM 30m DEM) processed in `district_terrain_summary.json`. |
| **ML Model** | Promoted Random Forest model (`candidate_a_rf_v1` v1.1.0) operating on a strict 7-feature contract. | `candidate_a_rf_v1.pkl` (SHA `1acad34e85...`). |
| **Validation Rigor** | Evaluated on an uncontaminated temporal holdout dataset (~0.9206 ROC-AUC, ~0.9328 PR-AUC, ~0.8258 F1, ~0.119 Brier). | Temporal evaluation benchmark in P5.5. |
| **Input Gating** | Missing rainfall inputs gate decision to `DATA_UNAVAILABLE` with `risk_probability = null`. | P0 safety gating in `risk_decision_engine.py`. |
| **Data Integrity** | Missing values remain `null` / `UNAVAILABLE` / `INSUFFICIENT DATA` without zero-filling. | P7C/P8 data completeness logic. |
| **Risk Decoupling** | Hazard Risk ($P \in [0, 1]$) and Vulnerability Score ($S \in [0, 100]$) remain 100% separate information cards. | UI layout in `App.tsx`. |
| **Explainability** | Model-level feature importances displayed; `local_explanation_available = false` explicitly declared. | `explainability_service.py`. |
| **Readiness Probe** | Operational `GET /api/ready` endpoint verifying runtime model load, SHA-256 integrity, and boundary files. | `backend/main.py`. |

---

## 2. Known System Limitations (What NexSolve DOES NOT Do)

| Area | Boundary & Limitation | Rationale & Governance Policy |
| :--- | :--- | :--- |
| **Warning Authority** | NexSolve does NOT possess official warning authority or trigger public evacuation alerts. | `is_official_warning = false` hardcoded across all responses. Official alerts remain the sole responsibility of SDMA/NDMA. |
| **Deterministic Prediction** | NexSolve does NOT predict exact landslide timing, volume, or runout path. | ML predictions represent statistical hazard probabilities ($P \in [0, 1]$) based on antecedent rainfall. |
| **Vulnerability Data Coverage** | Exposure profiles are scored for 16 districts (8 COMPUTED, 8 PARTIAL); 115 districts remain `INSUFFICIENT_DATA` with score `null`. | Complete open government dataset indicators are unavailable for all 131 districts. NexSolve avoids fabricating values. |
| **Terrain in ML Contract** | DEM terrain features (slope, aspect) are NOT included in the 7-feature ML prediction contract. | Features are presented alongside risk as environmental decision context to prevent ML model overfitting on static coordinates. |
| **Public Cloud Deployment** | Public cloud deployment status is recorded as `PUBLIC_CLOUD_DEPLOYMENT: NOT_VERIFIED`. | Containerized deployment configuration is prepared (`Dockerfile`, `docker-compose.yml`), but live deployment requires evaluator cloud project credentials. |
| **Local SHAP Values** | Local SHAP/LIME explanation values are NOT computed. | `local_explanation_available = false` is declared to avoid presenting unverified local attribution approximations. |

---

## 3. SIH Judge Presentation Boundaries Summary

- **DO**: Highlight our rigorous identification and elimination of earlier temporal leakage (replacing flawed 0.99+ estimates with uncontaminated 0.9206 ROC-AUC benchmark).
- **DO**: Emphasize our 131-district Survey of India boundary framework and USGS/AWS open data 30m DEM processing.
- **DO NOT**: Claim live integration with official government alert networks.
- **DO NOT**: Claim public cloud deployment or 100% vulnerability coverage across all districts.
