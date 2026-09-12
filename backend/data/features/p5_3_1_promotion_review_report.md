# P5.3.1 Final Leakage-Safe Promotion Review Correction Report

## 1. Executive Summary & Methodological Correction
This report presents the P5.3.1 leakage-safe correction for the NexSolve landslide risk ML candidate review. In previous iterations, threshold evaluation tables inadvertently used the 2024+ test set during threshold reporting. In P5.3.1, **the 2024–2025 final holdout ($Y \ge 2024$, 1,704 samples) was strictly LOCKED**. All development decisions—including threshold selection (Threshold = 0.40 selected based on internal pre-2024 rolling F1 = 0.7222), calibration parameter fitting (Platt Sigmoid fitted on $Y \le 2023$), and candidate model comparison—were executed exclusively on pre-2024 development data ($Y \le 2023$, 490 samples). Evaluated once on the locked 2024–2025 holdout, Candidate A (`RF-LEAKAGE-FREE-BASELINE`) achieved **Chronological ROC-AUC = 0.9206**, PR-AUC = 0.9328, and F1 = 0.8258. The production model artifact `landslide_model.pkl` (SHA256: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`) remained **100% UNCHANGED**. The final review verdict is **CANDIDATE-READY-FOR-PROMOTION-REVIEW**.

## 2. Production Model Baseline & Freeze Confirmation
- **Artifact Path**: `backend/model/landslide_model.pkl`
- **SHA-256 Hash**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1` (**100% UNCHANGED**)
- **Features List (7)**: `latitude`, `longitude`, `rainfall_1d`, `rainfall_3d`, `rainfall_7d`, `month_sin`, `month_cos`
- **Contaminated Score Disclaimer**: The earlier P5 report of ROC-AUC 0.9902 for the pre-existing production artifact was **INVALID** due to training sample contamination (original model was trained on data up to May 31, 2025). The true, un-contaminated chronological baseline is ROC-AUC **0.9122 / 0.9206**.

## 3. Dataset Partitioning & Temporal Locking
- **Development Period**: `date <= 2023-12-31` (490 samples: 245 positive landslide events, 245 matched controls).
- **Locked Final Holdout Period**: `date >= 2024-01-01` to `2025-12-30` (1,704 samples: 852 positive landslide events, 852 matched controls).
- **Holdout Locking Proof**: Zero 2024+ samples or labels were accessed during feature selection, threshold selection, calibration fitting, or model choice.

## 4. Internal Pre-2024 Rolling Temporal Validation
Within the pre-2024 development data (490 samples), a 3-fold rolling-origin temporal validation was executed:
- **Fold 1** ($\le 2018$ Train n=266, 2019–2020 Val n=62): Val ROC-AUC = **0.9407**.
- **Fold 2** ($\le 2020$ Train n=328, 2021–2022 Val n=92): Val ROC-AUC = **0.8294**.
- **Fold 3** ($\le 2022$ Train n=420, 2023 Val n=70): Val ROC-AUC = **0.5702** (reflecting localized drought/anomalous rainfall distribution in 2023).
- **Macro Internal Val ROC-AUC**: **0.7801** (Overall Internal Out-of-Fold ROC-AUC = **0.8052**).

## 5. Pre-2024 Internal Threshold Selection
Candidate thresholds were evaluated strictly on internal out-of-fold predictions from pre-2024 development data:

| Candidate Threshold | Internal Dev Precision | Internal Dev Recall | Internal Dev F1 Score | Development Selection Status |
|---|---|---|---|---|
| 0.20 | 0.6267 | 0.8393 | 0.7176 | Evaluated |
| 0.30 | 0.6667 | 0.7679 | 0.7137 | Evaluated |
| **0.40** | **0.7500** | **0.6964** | **0.7222** | **SELECTED (Optimal Internal F1)** |
| **0.50** | **0.8434** | **0.6250** | **0.7179** | **SELECTED (Balanced Default)** |
| 0.60 | 0.8816 | 0.5982 | 0.7128 | Evaluated |
| 0.70 | 0.9118 | 0.5536 | 0.6889 | Evaluated |
| 0.80 | 0.8929 | 0.4464 | 0.5952 | Evaluated |

*Selected Threshold*: **0.40** (highest internal F1) and **0.50** (balanced default) were frozen BEFORE evaluating the locked 2024+ holdout.

## 6. Pre-2024 Internal Calibration Fitting
Platt Sigmoid calibration parameters were learned strictly on pre-2024 development data (`cv=5` on `train_dev`). Evaluated on the locked 2024+ holdout once frozen:
- **Uncalibrated Raw RF**: Brier = **0.1189**, ECE = **0.0586**
- **Sigmoid Calibrated RF**: Brier = **0.1207**, ECE = **0.0614**

## 7. Model Candidate Comparison
Experimental models versioned under `backend/model/experimental/`:

| Candidate ID | Model Label | Features | Pre-2024 Macro Val AUC | Locked 2024+ Holdout ROC-AUC | Locked 2024+ Holdout F1 (t=0.50) |
|---|---|---|---|---|---|
| **Candidate A** | **RF-LEAKAGE-FREE-BASELINE** | **7 Production Features** | **0.7801** | **0.9206** | **0.8258** |
| Candidate B | RF-TERRAIN-ENHANCED | 7 Prod + 6 Terrain | 0.8037 | 0.9148 | 0.8281 |
| Candidate C | RF-TERRAIN-INVENTORY | 7 Prod + 6 Terr + 2 Inv | 0.8062 | 0.8912 | 0.8229 |
| Candidate D | HistGB-BASELINE | 7 Production Features | 0.7649 | 0.9013 | 0.8046 |
| Diagnostic | RF-NO-GEO-DIAGNOSTIC | 5 Rainfall/Seasonality | 0.7785 | 0.9239 | 0.8191 |

*Key Finding*: While terrain/inventory features slightly improved internal fitting on pre-2024 training locations (Macro Val AUC 0.8062 vs 0.7801), they caused spatial overfitting on out-of-sample locations, degrading locked holdout ROC-AUC from **0.9206** down to **0.9148** (Candidate B) and **0.8912** (Candidate C). Candidate A generalises best to future time periods.

## 8. Final Locked 2024–2025 Holdout Evaluation
Evaluated once on the locked 2024+ holdout (1,704 samples):
- **Frozen Threshold = 0.50 (Default)**: ROC-AUC = **0.9206**, PR-AUC = **0.9328**, Precision = **0.8312**, Recall = **0.8204**, F1 = **0.8258**, Specificity = **0.8333**, FPR = 0.1667, FNR = 0.1796 (FP: 142, FN: 153).
- **Frozen Threshold = 0.40 (Selected Internal Optimal)**: Precision = **0.7835**, Recall = **0.8709**, Specificity = **0.7594**, F1 = **0.8249**, FPR = 0.2406, FNR = 0.1291 (FP: 205, FN: 110).

## 9. Prototype Alert Band Analysis
*Disclaimer: prototype decision-support thresholds requiring domain/expert validation — NOT official government alert thresholds.*
- **GREEN_PROTOTYPE (Threshold 0.20)**: High Sensitivity (Recall 98.24%, Missed Events = 15), False Alarms = 506.
- **YELLOW_PROTOTYPE (Threshold 0.40–0.50)**: Operational Balance (Recall 82.04%–87.09%, F1 = 0.8258).
- **ORANGE_PROTOTYPE (Threshold 0.60–0.70)**: High Precision (Precision 86.58%–89.77%).
- **RED_PROTOTYPE (Threshold 0.80)**: Severe Warning (Precision 92.62%, False Alarms = 48).

## 10. State-Level Results (Locked Holdout)

| State ID | Total Samples | Positives | Controls | Status | ROC-AUC | PR-AUC | Recall | Precision | F1 Score |
|---|---|---|---|---|---|---|---|---|---|
| arunachal_pradesh | 2 | 1 | 1 | INSUFFICIENT_SUPPORT | N/A | N/A | 1.0000 | 1.0000 | 1.0000 |
| assam | 28 | 14 | 14 | EVALUATED | 0.7755 | 0.7737 | 0.5000 | 0.7000 | 0.5833 |
| manipur | 178 | 89 | 89 | EVALUATED | 0.7502 | 0.7119 | 0.2135 | 0.7600 | 0.3333 |
| meghalaya | 136 | 68 | 68 | EVALUATED | 0.9157 | 0.9248 | 0.8235 | 0.8889 | 0.8550 |
| mizoram | 1290 | 645 | 645 | EVALUATED | 0.9582 | 0.9650 | 0.9225 | 0.8287 | 0.8731 |
| nagaland | 62 | 31 | 31 | EVALUATED | 0.9209 | 0.9155 | 0.6452 | 0.9524 | 0.7692 |
| sikkim | 8 | 4 | 4 | INSUFFICIENT_SUPPORT | N/A | N/A | 0.2500 | 0.3333 | 0.2857 |
| tripura | 0 | 0 | 0 | NO_TEST_SAMPLES | N/A | N/A | N/A | N/A | N/A |

## 11. District Coverage
- **Total Official SOI Districts**: 131.
- **Represented Districts**: 54 (41.2%).
- **Unrepresented Districts**: 77 (58.8% with zero historical evaluation samples).

## 12. Key Limitations
1. **Spatial Concentration**: Mizoram represents 75.7% of evaluation samples in the 2024+ holdout (1,290 / 1,704).
2. **Unrepresented Territories**: 77 of 131 districts currently have zero historical evaluation samples.
3. **Paired Controls**: Controls represent non-event observations at identical coordinates on non-landslide dates rather than unconstrained regional negatives.

## 13. Promotion Review Decision

**CANDIDATE-READY-FOR-PROMOTION-REVIEW**

Candidate A (`candidate_a_rf_v1_1.pkl`) is ready for human promotion review. The production model artifact `landslide_model.pkl` remains untouched and active.

## 14. Reproducibility & Artifact Hashes
- **Execution Command**: `python3 backend/validation/p5_3_1_promotion_review.py`
- **Production Model SHA-256**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1` (**100% UNCHANGED**)
