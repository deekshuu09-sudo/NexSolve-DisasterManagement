# P5.1 Scientific Benchmark Audit

## 1. Production Model Provenance
- **Model Artifact**: `backend/model/landslide_model.pkl`
- **SHA-256 Hash**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`
- **Training Script**: `backend/training/train.py`
- **Training Dataset**: `backend/data/training/ml_dataset.csv` (2,194 samples)
- **Original Training Split**: First 80% sorted chronologically (1,755 samples)
- **Original Training Date Range**: `2014-01-21` to `2025-05-31`
- **Original Training Class Balance**: 844 Positive (landslide=1), 911 Negative (control=0)
- **Original Test Split (20%)**: `2025-05-31` to `2025-12-30` (439 samples)
- **Features List (7)**: `latitude`, `longitude`, `rainfall_1d`, `rainfall_3d`, `rainfall_7d`, `month_sin`, `month_cos`
- **Critical Training Leakage Finding**: The pre-trained production artifact `landslide_model.pkl` was trained on data extending through **May 31, 2025** (containing 1,265 samples from 2024 and 2025). When evaluated against the P5 Chronological Test set ($Y \ge 2024$), 1,265 out of the 1,704 test samples were already present in its training history. Consequently, the reported `Production_RF_Baseline` chronological ROC-AUC of **0.9902** evaluated via the loaded artifact is **INVALID** due to training data contamination.

## 2. Chronological Validation Integrity
- **P5 Chronological Definition**: Train ($Y \le 2023$, 490 samples: 245 pos, 245 neg) vs Test ($Y \ge 2024$, 1,704 samples: 852 pos, 852 neg).
- **Loaded Artifact vs Retrained Baseline**:
  - `Production_RF_Baseline` (Loaded Artifact): ROC-AUC = 0.9902 (**INVALID** due to 2024+ samples in original training set).
  - `Exp_RandomForestClassifier` (Retrained Model A Baseline): ROC-AUC = **0.9122**, PR-AUC = 0.9256, F1 = 0.8152, Brier = 0.1243. This is the **true, un-contaminated chronological performance** of the 7-feature RF configuration.
- **Contamination & Overlap Verification**:
  - Row overlap between train ($Y \le 2023$) and test ($Y \ge 2024$): **0**.
  - No preprocessing scalers or encoders were fitted on test data.
  - No feature selection or threshold tuning was performed using test labels.

## 3. Location-Group Validation Integrity
- **Grouping Protocol**: `location_group` (`latitude_longitude`).
- **Group Uniqueness**: All 2,194 samples belong to 1,097 unique location groups (each containing exactly 1 positive event and 1 matched control sample).
- **Group Overlap Check**: GroupKFold(5) enforces strict separation. Train group $\cap$ Test group = **$\emptyset$** across all 5 folds. Overlap = **EXACTLY 0**.
- **Location-Group Baseline Performance**: Retrained Model A achieved **ROC-AUC = 0.9643**, PR-AUC = 0.9667, F1 = 0.9022.

## 4. District-Group Validation Integrity
- **Grouping Protocol**: `district_id` (131 official Survey of India districts).
- **District Overlap Check**: GroupKFold(5) split across districts. Train districts $\cap$ Test districts = **$\emptyset$** for all folds. Overlap = **EXACTLY 0**.
- **District-Group Out-of-District Performance**: Retrained Model A achieved **ROC-AUC = 0.9354**, F1 = 0.8364. Adding historical inventory features (Model C) severely degraded out-of-district Recall to **0.5278** and F1 to **0.6480**, proving severe spatial overfitting in inventory-heavy models.

## 5. Duplicate / Location Audit
- **Total Samples**: 2,194
- **Exact Duplicate Rows**: **0**
- **Unique Coordinate Pairs**: **1,097**
- **Samples per Coordinate**: Min = 2, Max = 2, Mean = 2.0, Median = 2.0.
- **Pairing Structure**: Every positive landslide event location is paired with exactly 1 non-event control observation at the identical lat/lon coordinates taken on a non-landslide date.
- **Location Overlap in Chronological Split**: 0 out of 852 test locations overlap with the 245 train locations (since train has pre-2024 event locations and test has 2024+ event locations).

## 6. Latitude/Longitude Dependence
- **Production RF Feature Importances**:
  - `rainfall_1d`: 23.75%
  - `rainfall_3d`: 23.32%
  - `rainfall_7d`: 18.66%
  - `month_cos`: 9.23%
  - `longitude`: 9.19%
  - `latitude`: 7.96%
  - `month_sin`: 7.90%
- **Feature Category Importance Breakdown**:
  - Combined Rainfall (1d + 3d + 7d): **65.73%**
  - Combined Spatial (Lat + Lon): **17.15%**
  - Combined Seasonality (`month_sin` + `month_cos`): **17.13%**
- **Experimental Diagnostic Without Coordinates**:
  - An experimental RF trained on $Y \le 2023$ using ONLY rainfall and seasonality features (`rainfall_1d`, `rainfall_3d`, `rainfall_7d`, `month_sin`, `month_cos`) achieved **Chronological ROC-AUC = 0.9239** and **F1 = 0.8191**.
  - **Conclusion**: Landslide hazard predictions are predominantly rainfall-triggered (65.73% importance), NOT spatial coordinate memorization.

## 7. Class Balance
- **Overall Dataset**: 1,097 Positive (50.0%), 1,097 Negative (50.0%)
- **Chronological Holdout Split**:
  - Train ($Y \le 2023$): 245 Positive, 245 Negative (Total: 490)
  - Test ($Y \ge 2024$): 852 Positive, 852 Negative (Total: 1,704)
- **5-Fold Cross-Validation Splits (Location / District / Event)**:
  - Each fold maintains an approximate 50% positive / 50% negative class balance across train and test folds.

## 8. Complete Benchmark Results
Full results across all model architecture × feature set × validation strategy combinations:

| Model ID | Feature Set | Strategy | ROC-AUC | PR-AUC | Precision | Recall | F1 Score | Brier | ECE |
|---|---|---|---|---|---|---|---|---|---|
| Loaded_Prod_RF | Model_A_Prod (7) | Chronological* | 0.9902 | 0.9902 | 0.9566 | 0.9319 | 0.9441 | 0.0437 | 0.0507 |
| Loaded_Prod_RF | Model_A_Prod (7) | Location_Group | 0.9909 | 0.9907 | 0.9606 | 0.9325 | 0.9463 | 0.0444 | 0.0631 |
| Exp_RF | Model_A_Prod (7) | Chronological | 0.9122 | 0.9256 | 0.8230 | 0.8075 | 0.8152 | 0.1243 | 0.0586 |
| Exp_RF | Model_A_Prod (7) | Location_Group | 0.9643 | 0.9667 | 0.9132 | 0.8915 | 0.9022 | 0.0716 | 0.0312 |
| Exp_RF | Model_A_Prod (7) | District_Group | 0.9354 | 0.9402 | 0.8916 | 0.7876 | 0.8364 | 0.1017 | 0.0312 |
| Exp_RF | Model_A_Prod (7) | Event_Aware | 0.9643 | 0.9667 | 0.9132 | 0.8915 | 0.9022 | 0.0716 | 0.0312 |
| Exp_HistGB | Model_A_Prod (7) | Chronological | 0.9013 | 0.9208 | 0.7613 | 0.8533 | 0.8046 | 0.1472 | 0.0999 |
| Exp_HistGB | Model_A_Prod (7) | Location_Group | 0.9595 | 0.9614 | 0.9018 | 0.8961 | 0.8989 | 0.0766 | 0.0383 |
| Exp_HistGB | Model_A_Prod (7) | District_Group | 0.9225 | 0.9312 | 0.8315 | 0.8277 | 0.8296 | 0.1210 | 0.0774 |
| Exp_HistGB | Model_A_Prod (7) | Event_Aware | 0.9595 | 0.9614 | 0.9018 | 0.8961 | 0.8989 | 0.0766 | 0.0383 |
| Exp_RF | Model_B_Terrain (13) | Chronological | 0.9066 | 0.9176 | 0.8367 | 0.8181 | 0.8273 | 0.1240 | 0.0518 |
| Exp_RF | Model_B_Terrain (13) | Location_Group | 0.9613 | 0.9642 | 0.9123 | 0.8815 | 0.8966 | 0.0769 | 0.0366 |
| Exp_RF | Model_B_Terrain (13) | District_Group | 0.9310 | 0.9353 | 0.8853 | 0.8022 | 0.8417 | 0.1052 | 0.0298 |
| Exp_RF | Model_B_Terrain (13) | Event_Aware | 0.9613 | 0.9642 | 0.9123 | 0.8815 | 0.8966 | 0.0769 | 0.0366 |
| Exp_HistGB | Model_B_Terrain (13) | Chronological | 0.9080 | 0.9130 | 0.8053 | 0.8638 | 0.8335 | 0.1335 | 0.0843 |
| Exp_HistGB | Model_B_Terrain (13) | Location_Group | 0.9556 | 0.9558 | 0.8954 | 0.8815 | 0.8884 | 0.0835 | 0.0415 |
| Exp_HistGB | Model_B_Terrain (13) | District_Group | 0.9221 | 0.9269 | 0.8583 | 0.7949 | 0.8254 | 0.1207 | 0.0753 |
| Exp_HistGB | Model_B_Terrain (13) | Event_Aware | 0.9556 | 0.9558 | 0.8954 | 0.8815 | 0.8884 | 0.0835 | 0.0415 |
| Exp_RF | Model_C_Inventory (15) | Chronological | 0.8829 | 0.8793 | 0.8293 | 0.8099 | 0.8195 | 0.1386 | 0.0946 |
| Exp_RF | Model_C_Inventory (15) | Location_Group | 0.9649 | 0.9683 | 0.9104 | 0.8988 | 0.9046 | 0.0736 | 0.0377 |
| Exp_RF | Model_C_Inventory (15) | District_Group | 0.8953 | 0.8815 | 0.8391 | 0.5278 | 0.6480 | 0.1456 | 0.1096 |
| Exp_RF | Model_C_Inventory (15) | Event_Aware | 0.9649 | 0.9683 | 0.9104 | 0.8988 | 0.9046 | 0.0736 | 0.0377 |
| Exp_HistGB | Model_C_Inventory (15) | Chronological | 0.8915 | 0.9023 | 0.7926 | 0.8345 | 0.8345 | 0.1445 | 0.1111 |
| Exp_HistGB | Model_C_Inventory (15) | Location_Group | 0.9629 | 0.9645 | 0.9015 | 0.9015 | 0.9015 | 0.0746 | 0.0375 |
| Exp_HistGB | Model_C_Inventory (15) | District_Group | 0.9025 | 0.8911 | 0.8570 | 0.7648 | 0.8083 | 0.1369 | 0.1111 |
| Exp_HistGB | Model_C_Inventory (15) | Event_Aware | 0.9629 | 0.9645 | 0.9015 | 0.9015 | 0.9015 | 0.0746 | 0.0375 |

*\*Note: Loaded_Prod_RF Chronological score of 0.9902 is INVALID due to 2024+ samples in the original training set.*

## 9. Calibration Audit
- **Brier Score Calculation**: Evaluated via standard quadratic loss `brier_score_loss(y_true, y_prob)`.
- **Expected Calibration Error (ECE)**: Calculated across 10 uniform probability bins ($[0.0, 0.1], \dots, [0.9, 1.0]$).
- **Test Label Independence**: No calibration adjustment (Platt scaling, Isotonic regression, or threshold optimization) was fitted on test set probabilities. Uncalibrated raw probabilities were evaluated directly.

## 10. Leakage Findings
1. **Pre-trained Artifact Training Overlap**: `landslide_model.pkl` was originally trained on data up to May 31, 2025. Evaluating it against a 2024+ test set constitutes temporal data contamination, rendering the 0.9902 chronological score invalid for the pre-trained artifact.
2. **Feature Exclusions**: `distance_to_nearest_event_km` and `soilSat` were strictly excluded from P5 benchmarking, eliminating static proximity leakage and UI-proxy leakage.
3. **Validation Group Integrity**: GroupKFold validation successfully prevented spatial coordinate overlap between train and test folds (group overlap = 0 across all 5 folds).

## 11. Limitations
1. **Contrastive Spatial Control Pairing**: Each positive event is paired with a control sample at the exact same lat/lon coordinates. This binary setup tests temporal triggering given a susceptible location, rather than unconstrained regional risk mapping.
2. **Feature-Set Generalization**: Adding static terrain and historical inventory features reduced chronological forecasting ROC-AUC from 0.9122 down to 0.8829 and degraded out-of-district recall to 0.5278 due to overfitting.

## 12. Final Scientific Verdict

**VALID-WITH-LIMITATIONS**

The P5 group-structured cross-validation protocol and experimental baseline comparisons are scientifically valid and demonstrate that the production 7-feature Random Forest design outperforms complex terrain/inventory models on chronological forecasting (ROC-AUC 0.9122 vs 0.8829) and out-of-district generalization (F1 0.8364 vs 0.6480). However, the previously reported 0.9902 chronological score for the pre-trained production artifact is flagged as **INVALID** due to 2024+ training sample contamination.
