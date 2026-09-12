# P5.3 Independent Model Promotion Review Report

## 1. Executive Summary
This report presents an independent, leakage-free scientific review of the NexSolve landslide risk ML candidate models. The evaluation compares Candidate A (`RF-LEAKAGE-FREE-BASELINE`), Candidate B (`RF-TERRAIN-ENHANCED`), Candidate C (`RF-TERRAIN-INVENTORY-ENHANCED`), and Candidate D (`HistGB-LEAKAGE-FREE-BASELINE`) against the current production model architecture. The production model artifact `backend/model/landslide_model.pkl` (SHA256: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`) remained **100% UNCHANGED** throughout the audit. Candidate A (`RF-LEAKAGE-FREE-BASELINE`) achieved a leakage-free chronological ROC-AUC of **0.9206** (PR-AUC 0.9328, F1 0.8258), outperforming complex terrain and inventory models. The final promotion decision is **CANDIDATE-READY-FOR-PROMOTION-REVIEW**, recommending formal promotion authorization before replacing the production artifact.

## 2. Validation Objective
To rigorously evaluate candidate models under strict temporal and spatial leakage controls, ensuring no future information ($Y \ge 2024$) was used during training, hyperparameter selection, calibration, or threshold tuning.

## 3. Production Model Baseline
- **Artifact Path**: `backend/model/landslide_model.pkl`
- **SHA-256 Hash**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`
- **Production Features (7)**: `latitude`, `longitude`, `rainfall_1d`, `rainfall_3d`, `rainfall_7d`, `month_sin`, `month_cos`
- **Status**: Frozen and 100% UNCHANGED.
- **Contaminated Score Note**: The previously reported 0.9902 chronological score for the pre-existing production artifact was flagged as **INVALID** due to training overlap (original artifact contained data extending through May 31, 2025). The true, un-contaminated chronological baseline is ROC-AUC **0.9122 / 0.9206**.

## 4. Candidate Models
Stored as versioned artifacts under `backend/model/experimental/`:
1. **Candidate A (`candidate_a_rf_v1.pkl`)**: `RandomForestClassifier` with 7 production features (`n_estimators=300, max_depth=12, class_weight='balanced', random_state=42`).
2. **Candidate B (`candidate_b_rf_v1.pkl`)**: Candidate A + 6 static terrain features (`elevation_m`, `slope_deg`, `aspect_deg`, `curvature`, `district_mean_slope`, `district_p90_slope`).
3. **Candidate C (`candidate_c_rf_v1.pkl`)**: Candidate B + 2 historical inventory features (`historical_event_count`, `event_density_per_sqkm`). Excludes `distance_to_nearest_event_km` and `soilSat`.
4. **Candidate D (`candidate_d_histgb_v1.pkl`)**: `HistGradientBoostingClassifier` with 7 production features (`max_iter=100, random_state=42`).

## 5. Dataset and Temporal Coverage
- **Total Fused Samples**: 2,194 samples (1,097 landslide events, 1,097 paired control observations).
- **Training Period**: `date <= 2023-12-31` (490 samples: 245 positive, 245 control).
- **Untouched Test Period**: `date >= 2024-01-01` (1,704 samples: 852 positive, 852 control).

## 6. Leakage Controls
- **Zero Future Data Contamination**: All candidate models were fitted exclusively on $Y \le 2023$ data.
- **Excluded Features**: `distance_to_nearest_event_km` (static 0-distance artifact) and `soilSat` (UI-simulated proxy) were strictly excluded.
- **Inventory Temporal Safety**: Features respect P4.1.2 temporal resolution rules (`event_date <= prediction_date`).

## 7. Rolling Temporal Validation
Evaluated strictly within pre-2024 data ($Y \le 2023$):
- **Fold 1** ($\le 2018$ Train, 2019–2021 Test): Candidate A ROC-AUC = **0.8845**, F1 = **0.8125**.
- **Fold 2** ($\le 2021$ Train, 2022–2023 Test): Candidate A ROC-AUC = **0.8912**, F1 = 0.8169.
- Demonstrates consistent stability as the historical training window expands.

## 8. Final 2024–2025 Holdout Results
Evaluated on the untouched test set (1,704 samples):
- **Candidate A (`RF-LEAKAGE-FREE-BASELINE`)**: **ROC-AUC = 0.9206**, PR-AUC = 0.9328, Precision = 0.8312, Recall = 0.8204, F1 = 0.8258, Specificity = 0.8333, Brier = 0.1189, ECE = 0.0586.
- **Candidate B (`RF-TERRAIN-ENHANCED`)**: ROC-AUC = 0.9148, PR-AUC = 0.9219, Precision = 0.8335, Recall = 0.8228, F1 = 0.8281, Brier = 0.1206.
- **Candidate C (`RF-TERRAIN-INVENTORY-ENHANCED`)**: ROC-AUC = 0.8912, PR-AUC = 0.8924, Precision = 0.8196, Recall = 0.8263, F1 = 0.8229, Brier = 0.1347.
- **Candidate D (`HistGB-LEAKAGE-FREE-BASELINE`)**: ROC-AUC = 0.9013, PR-AUC = 0.9208, Precision = 0.7613, Recall = 0.8533, F1 = 0.8046, Brier = 0.1472.

## 9. Spatial Group Validation
- **Location-Group 5-Fold CV**: 1,097 unique coordinate groups. Train $\cap$ Test overlap = **0**. Candidate A ROC-AUC = **0.9644**, PR-AUC = 0.9669, F1 = 0.9033.
- **District-Group 5-Fold CV**: 131 official Survey of India districts. Train $\cap$ Test overlap = **0**. Candidate A ROC-AUC = **0.9347**, PR-AUC = 0.9403, F1 = 0.8428.
- **State-Group 5-Fold CV**: 8 Northeastern states. Train $\cap$ Test overlap = **0**. Candidate A ROC-AUC = **0.9112**, F1 = 0.8214.

## 10. State-Level Results

| State ID | Total Samples | Positive Count | Control Count | Status | ROC-AUC | PR-AUC | Recall | Precision | F1 Score |
|---|---|---|---|---|---|---|---|---|---|
| arunachal_pradesh | 2 | 1 | 1 | INSUFFICIENT_SUPPORT | N/A | N/A | 1.0000 | 1.0000 | 1.0000 |
| assam | 28 | 14 | 14 | EVALUATED | 0.7755 | 0.7737 | 0.5000 | 0.7000 | 0.5833 |
| manipur | 178 | 89 | 89 | EVALUATED | 0.7502 | 0.7119 | 0.2135 | 0.7600 | 0.3333 |
| meghalaya | 136 | 68 | 68 | EVALUATED | 0.9157 | 0.9248 | 0.8235 | 0.8889 | 0.8550 |
| mizoram | 1290 | 645 | 645 | EVALUATED | 0.9582 | 0.9650 | 0.9225 | 0.8287 | 0.8731 |
| nagaland | 62 | 31 | 31 | EVALUATED | 0.9209 | 0.9155 | 0.6452 | 0.9524 | 0.7692 |
| sikkim | 8 | 4 | 4 | INSUFFICIENT_SUPPORT | N/A | N/A | 0.2500 | 0.3333 | 0.2857 |
| tripura | 0 | 0 | 0 | NO_TEST_SAMPLES | N/A | N/A | N/A | N/A | N/A |

## 11. District-Level Results
- **Official SOI NER Districts**: 131 districts.
- **Evaluated Districts**: 54 districts represented in fused dataset (41.2%).
- **Unevaluated Districts**: 77 districts with zero historical samples (58.8%).
- **Strongest Performing Districts**: Aizawl (ROC-AUC 0.9680), Lunglei (ROC-AUC 0.9612), East Khasi Hills (ROC-AUC 0.9420).
- **Weakest / Variable Districts**: Imphal West (ROC-AUC 0.7120), Kamrup Metropolitan (ROC-AUC 0.7250).

## 12. Event-Aware Validation
Controls are strictly designated as `CONTROL / NON-EVENT OBSERVATIONS` (non-event dates at identical coordinates), NOT confirmed negatives. P4.1.2 temporal resolution rules are strictly enforced.

## 13. Calibration Analysis
- Candidate A achieved native Brier score = **0.1189** and ECE = **0.0586**.
- Post-hoc Platt Sigmoid scaling slightly increased Brier score to 0.1207 due to small sample size in pre-2024 training data. Raw tree ensemble probabilities are recommended.

## 14. Threshold Analysis
*Disclaimer: PROTOTYPE DECISION THRESHOLDS — NOT OFFICIAL GOVERNMENT ALERT THRESHOLDS*

| Threshold | Risk Band Prototype | Precision | Recall | Specificity | FPR | FNR | F1 Score | FP | FN |
|---|---|---|---|---|---|---|---|---|---|
| 0.20 | GREEN_PROTOTYPE (High Sensitivity) | 0.6232 | 0.9824 | 0.4061 | 0.5939 | 0.0176 | 0.7626 | 506 | 15 |
| 0.30 | GREEN_PROTOTYPE (Early Warning) | 0.7145 | 0.9343 | 0.6268 | 0.3732 | 0.0657 | 0.8098 | 318 | 56 |
| 0.40 | YELLOW_PROTOTYPE (Operational) | 0.7835 | 0.8709 | 0.7594 | 0.2406 | 0.1291 | 0.8249 | 205 | 110 |
| 0.50 | YELLOW_PROTOTYPE (Balanced Default) | 0.8312 | 0.8204 | 0.8333 | 0.1667 | 0.1796 | 0.8258 | 142 | 153 |
| 0.60 | ORANGE_PROTOTYPE (Elevated Alert) | 0.8658 | 0.7723 | 0.8803 | 0.1197 | 0.2277 | 0.8164 | 102 | 194 |
| 0.70 | ORANGE_PROTOTYPE (High Alert) | 0.8977 | 0.7312 | 0.9167 | 0.0833 | 0.2688 | 0.8060 | 71 | 229 |
| 0.80 | RED_PROTOTYPE (Severe Warning) | 0.9262 | 0.7066 | 0.9437 | 0.0563 | 0.2934 | 0.8016 | 48 | 250 |

## 15. False Alarm vs Missed Event Analysis
In landslide disaster mitigation, false negatives (missed events) carry life-safety risks, while false positives (false alarms) cause evacuation fatigue.
- At **Threshold = 0.20**, missed events drop to **15** (FNR 1.76%), but false alarms rise to 506 (FPR 59.39%).
- At **Threshold = 0.50**, false alarms (142) and missed events (153) are balanced (F1 = 0.8258).

## 16. Terrain Feature Value
Adding 6 static DEM terrain features (Candidate B) slightly reduced chronological ROC-AUC from 0.9206 to 0.9148. Static terrain features overfit pre-2024 location geometry.

## 17. Inventory Feature Value
Adding historical inventory features (Candidate C) further degraded chronological ROC-AUC to 0.8912 and out-of-district recall to 0.7894. Inventory features do NOT provide defensible out-of-sample improvement.

## 18. Missing Data Robustness
Backend services (`feature_engineering_service.py` and prediction APIs) enforce strict explicit null handling. When rainfall, terrain, or inventory inputs are unavailable, services return explicit error/unavailable statuses rather than silently imputing zero.

## 19. Model Stability
Candidate A demonstrated low variance across random seeds ($\pm 0.0012$ ROC-AUC) and stable temporal fold progression (0.8845 $\rightarrow$ 0.8912 $\rightarrow$ 0.9206).

## 20. Limitations
- **Spatial Coverage Concentration**: 1,290 out of 1,704 test samples are in Mizoram. 77 out of 131 districts have 0 evaluation samples.
- **Paired Controls**: Controls are sampled at identical lat/lon coordinates on non-event dates.

## 21. Promotion Decision

**CANDIDATE-READY-FOR-PROMOTION-REVIEW**

Candidate A (`candidate_a_rf_v1.pkl`) is ready for human promotion review. The production model artifact `landslide_model.pkl` remains untouched and active.

## 22. Reproducibility
Can be reproduced by running `python3 backend/validation/p5_3_promotion_review.py`.

## 23. Artifact Hashes
- Production Model `landslide_model.pkl`: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1` (**UNCHANGED**)
- Candidate A `candidate_a_rf_v1.pkl`: SHA-256 verified in registry.
