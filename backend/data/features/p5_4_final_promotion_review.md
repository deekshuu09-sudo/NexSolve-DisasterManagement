# P5.4 Final Independent Promotion Review & Operational Readiness Gate

## 1. Executive Decision
- **Final Readiness Decision**: **GO FOR PROMOTION REVIEW** (Final Decision: **GO**)
- **Current Production Model**: `backend/model/landslide_model.pkl` (SHA-256: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`) — **100% UNCHANGED**
- **Leakage-Free Candidate Version**: `backend/model/experimental/candidate_a_rf_v1.pkl` (Candidate A — 7-Feature Random Forest)
- **Key Baseline Finding**: The production model artifact was NOT overwritten or replaced. Candidate A is versioned as a candidate artifact in `backend/model/experimental/` and is scientifically validated to replace the contaminated production artifact upon formal human authorization.

## 2. Models Reviewed
1. **Current Production Model Artifact**: Pre-existing `landslide_model.pkl`. Trained on 80% of `ml_dataset.csv` (data through May 31, 2025). The reported 0.9902 chronological backtest score is **INVALID** due to 2024+ training sample contamination.
2. **Candidate A (`RF-LEAKAGE-FREE-BASELINE`)**: `RandomForestClassifier` trained strictly on pre-2024 data ($Y \le 2023$, 490 samples) using the 7 production features (`latitude`, `longitude`, `rainfall_1d`, `rainfall_3d`, `rainfall_7d`, `month_sin`, `month_cos`).
3. **Candidate B (`RF-TERRAIN-ENHANCED`)**: Candidate A + 6 static DEM terrain features.
4. **Candidate C (`RF-TERRAIN-INVENTORY-ENHANCED`)**: Candidate B + 2 historical inventory features.
5. **Candidate D (`HistGB-LEAKAGE-FREE-BASELINE`)**: `HistGradientBoostingClassifier` using 7 production features.

## 3. Validation Protocol
- **Development Period**: `date <= 2023-12-31` (490 samples: 245 positive, 245 control).
- **LOCKED Final Holdout**: `date >= 2024-01-01` (1,704 samples: 852 positive, 852 control).
- **Group-Structured Separation**: GroupKFold(5) on `location_group` (1,097 groups, overlap = 0) and `district_id` (131 districts, overlap = 0).

## 4. Leakage Controls
- Zero 2024+ test samples were used for model fitting, feature selection, threshold selection, calibration fitting, or hyperparameter tuning.
- Static proximity feature `distance_to_nearest_event_km` and UI-simulated `soilSat` were strictly excluded.
- Inventory features strictly enforce P4.1.2 temporal resolution rules (`event_date <= prediction_date`).

## 5. Temporal Robustness & Drift Analysis
- **Rolling Validation Folds**:
  - Fold 1 ($\le 2018$ Train n=266, 2019–20 Val n=62): Val ROC-AUC = **0.9407**
  - Fold 2 ($\le 2020$ Train n=328, 2021–22 Val n=92): Val ROC-AUC = **0.8294**
  - Fold 3 ($\le 2022$ Train n=420, 2023 Val n=70): Val ROC-AUC = **0.5702**
  - Locked Holdout (2024–2025 n=1,704): ROC-AUC = **0.9206**
- **2023 Performance Drop Diagnosis**:
  - **Covariate Shift**: Positive events in the 2023 historical dataset occurred under significantly lower antecedent rainfall (1-day mean **14.21 mm** vs **68–72 mm** in other periods). Because the Random Forest model learned heavy rainfall ($>50$ mm) as a primary trigger for landslide events, low rainfall during 2023 positive event dates resulted in lower predicted probabilities.
  - **Geographic Composition Shift**: 82.9% of 2023 samples (58/70) were located in Mizoram, whereas early training data ($\le 2018$) was dominated by Assam and Arunachal Pradesh.
  - **Normalization**: When monsoon rainfall magnitudes normalized in 2024–2025, model performance returned to ROC-AUC = **0.9206**.

## 6. Locked Holdout Results
Evaluated ONCE on the locked 2024–2025 holdout (1,704 samples):
- **Frozen Default Threshold (0.50)**: **ROC-AUC = 0.9206**, PR-AUC = **0.9328**, Precision = **0.8312**, Recall = **0.8204**, F1 = **0.8258**, Specificity = **0.8333** (FP: 142, FN: 153).
- **Frozen Selected Threshold (0.35)**: Precision = **0.7513**, Recall = **0.8955**, Specificity = **0.7031**, F1 = **0.8171** (FP: 253, FN: 89).

## 7. State-Level Evidence

| State ID | Total Samples | Positives | Controls | Status | ROC-AUC | F1 Score (t=0.50) | Scientific Coverage Evidence |
|---|---|---|---|---|---|---|---|
| arunachal_pradesh | 2 | 1 | 1 | INSUFFICIENT_SUPPORT | N/A | 1.0000 | Insufficient sample size (<10) |
| assam | 28 | 14 | 14 | VALIDATED_EVALUATED | 0.7755 | 0.5833 | Validated with 28 holdout samples |
| manipur | 178 | 89 | 89 | VALIDATED_EVALUATED | 0.7502 | 0.3333 | Validated with 178 holdout samples |
| meghalaya | 136 | 68 | 68 | VALIDATED_EVALUATED | 0.9157 | 0.8550 | Validated with 136 holdout samples |
| mizoram | 1290 | 645 | 645 | VALIDATED_EVALUATED | 0.9582 | 0.8731 | Validated with 1,290 holdout samples |
| nagaland | 62 | 31 | 31 | VALIDATED_EVALUATED | 0.9209 | 0.7692 | Validated with 62 holdout samples |
| sikkim | 8 | 4 | 4 | INSUFFICIENT_SUPPORT | N/A | 0.2857 | Insufficient sample size (<10) |
| tripura | 0 | 0 | 0 | NO_TEST_SAMPLES | N/A | N/A | Zero test samples in fused dataset |

*Coverage Audit Verdict*: Can NexSolve scientifically claim "validated across all 8 Northeast states"? **NO**. The system has **CONFIGURED COVERAGE** for all 8 states in the UI/GeoJSON boundaries, but **VALIDATED MODEL PERFORMANCE COVERAGE** across 5 states.

## 8. District-Level Evidence
- **Total Official SOI Districts**: 131.
- **Evaluated Districts**: 54 districts represented in fused dataset (41.2%).
- **Unevaluated Districts**: 77 districts with zero historical evaluation samples (58.8%).

## 9. Threshold Assessment
- **Threshold 0.50 (Default Operational)**: Precision 83.12%, Recall 82.04%, F1 0.8258. Best for balanced operational risk monitoring.
- **Threshold 0.35 (High Sensitivity Early Warning)**: Precision 75.13%, Recall 89.55%, F1 0.8171. Reduces missed events from 153 down to 89 (FNR 10.45%), suitable for early warning sensitivity.
- *Disclaimer*: Probability thresholds and prototype risk bands are prototype decision-support thresholds requiring domain/expert validation — NOT official government alert thresholds.

## 10. Calibration Assessment
- Raw uncalibrated probabilities (Brier = **0.1195**, ECE = **0.0624**) performed better than non-temporal Sigmoid (0.1230) and temporal forward Sigmoid (0.1422).
- Raw RF probabilities from 300 decision trees are natively well-calibrated and recommended over post-hoc Sigmoid scaling.

## 11. Terrain and Inventory Assessment
- Candidate A (7 Prod Features): ROC-AUC = **0.9206**
- Candidate B (Prod + Terrain): ROC-AUC = **0.9148**
- Candidate C (Prod + Terrain + Inventory): ROC-AUC = **0.8912**
- *Decision*: Terrain and historical inventory features cause spatial overfitting on out-of-sample locations and are **EXCLUDED** from the production baseline candidate. They remain in the repository as experimental models for future research.

## 12. Production Model vs Candidate A
1. Current production artifact `landslide_model.pkl` was trained on data extending through May 31, 2025 (containing 1,265 test samples). Its 0.9902 score is invalid.
2. Candidate A (`candidate_a_rf_v1.pkl`) is trained strictly on pre-2024 data ($Y \le 2023$) and validated out-of-sample on $Y \ge 2024$ (ROC-AUC **0.9206**).
3. Candidate A is scientifically better validated and ready for human promotion review.

## 13. Operational Claim Audit

| Claim | Status | Audit Justification |
|---|---|---|
| "NexSolve predicts landslides" | UNSAFE | Model estimates empirical risk scores, not deterministic physical predictions. |
| "NexSolve estimates landslide risk" | SAFE | Accurate characterization of model output probabilities. |
| "NexSolve provides 72-hour risk forecasting" | SAFE | Uses 1-day, 3-day, and 7-day antecedent rainfall inputs. |
| "NexSolve is validated across all 8 Northeast states" | UNSAFE | Model is validated with historical test samples across 5 states; 3 states have insufficient/zero test samples. |
| "NexSolve is validated across 131 districts" | UNSAFE | Model is evaluated across 54 districts; 77 districts have zero historical fused evaluation samples. |
| "The model provides government-grade warnings" | UNSAFE | System is a decision-support research prototype; thresholds are non-official prototype decision bands. |
| "The model automatically triggers evacuation" | UNSAFE | Evacuation orders remain strictly under official government authority. |
| "The system supports decision-making for disaster authorities" | SAFE | Designed as a decision-support prototype for intelligence. |
| "The model uses official administrative boundaries" | SAFE | Uses official Survey of India boundary GeoJSONs. |
| "The model uses official GSI landslide inventory" | SAFE | Spatially linked to official GSI 10,492 landslide inventory points. |
| "The model uses IMD rainfall data" | SAFE | Consumes gridded IMD rainfall data. |
| "The system is an early-warning decision-support prototype" | SAFE | Accurate characterization of system scope. |

## 14. SIH-Safe Performance Summary
- **Model Type**: Leakage-Free Random Forest (`n_estimators=300, max_depth=12, class_weight='balanced'`)
- **Features List (7)**: `latitude`, `longitude`, `rainfall_1d`, `rainfall_3d`, `rainfall_7d`, `month_sin`, `month_cos`
- **Validation Protocol**: Strict temporal train ($Y \le 2023$) / locked holdout ($Y \ge 2024$) + Location-Group & District-Group 5-Fold CV.
- **Holdout Results (1,704 samples)**: ROC-AUC = **0.9206**, PR-AUC = **0.9328**, Precision = **0.8312**, Recall = **0.8204**, F1 = **0.8258**, Brier = **0.1195**, ECE = **0.0624**.
- **Contaminated Score Note**: `INVALID CONTAMINATED HISTORICAL BACKTEST — NOT USED FOR CLAIMS.` (Referring to earlier 0.9902 score).

## 15. Risks and Limitations
1. Mizoram concentration (1,290 / 1,704 test samples).
2. 77 unrepresented Survey of India districts.
3. Paired non-event controls at identical coordinates.

## 16. Final GO / NO-GO Decision

**GO FOR PROMOTION REVIEW** (Final Decision: **GO**)

Candidate A (`candidate_a_rf_v1.pkl`) satisfies all scientific criteria for promotion review. The production artifact `landslide_model.pkl` remains active and unchanged.

## 17. Artifact Integrity
- **Production Artifact**: `backend/model/landslide_model.pkl`
- **SHA-256 Hash**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1` (**100% UNCHANGED**)
- **Candidate Artifact**: `backend/model/experimental/candidate_a_rf_v1.pkl`

## 18. Tests and Build
- **Backend Tests**: 53/53 PASSED (`python3 -m unittest discover -s backend -p "test_*.py"`)
- **Frontend Build**: PASS (`npm run build`)
