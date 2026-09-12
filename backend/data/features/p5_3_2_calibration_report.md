# P5.3.2 Calibration Audit Report

## 1. Objective & Context
To audit probability calibration methodology and compare:
1. Raw `RandomForestClassifier` probabilities
2. Non-temporal 5-fold Sigmoid calibration (`CalibratedClassifierCV(cv=5)`)
3. Temporally safe forward-chaining Platt Sigmoid calibration (fitted on pre-2024 rolling splits)

All calibration models were fitted **strictly on pre-2024 development data** ($Y \le 2023$, 490 samples) and evaluated on the locked 2024–2025 holdout ($Y \ge 2024$, 1,704 samples).

## 2. Calibration Audit Results (Evaluated on Locked Holdout)

| Calibration Strategy | Development Fitting Protocol | Brier Score | ECE (Expected Calibration Error) | Empirical Finding |
|---|---|---|---|---|
| **Raw Uncalibrated RF** | Native Probability Output (300 Trees) | **0.1195** | **0.0624** | **SUPERIOR (Lowest Brier & ECE)** |
| Non-temporal 5-Fold Sigmoid | `CalibratedClassifierCV(cv=5)` on Dev Data | 0.1230 | 0.0866 | Slight degradation due to CV estimation noise |
| Temporal Forward Sigmoid | Logistic Regression on Forward OOF Predictions | 0.1422 | 0.1741 | Significant degradation due to small OOF sample size |

## 3. Scientific Analysis & Recommendation
- **Native Ensemble Calibration**: `RandomForestClassifier` (300 trees, `max_depth=12`, `class_weight='balanced'`) natively yields well-calibrated probabilities. Averaging predictions across 300 decision trees trained on balanced bootstrap samples provides intrinsic probability smoothing.
- **Why Post-Hoc Scaling Degrades Performance**: On small historical training datasets (490 development samples), fitting a 2-parameter logistic sigmoid transformation on out-of-fold predictions introduces small-sample estimation variance that distorts the native probability distribution.
- **Final Recommendation**: Raw uncalibrated probabilities from Candidate A (`RF-LEAKAGE-FREE-BASELINE`) are scientifically preferred. Probabilities should be presented as model confidence / risk scores rather than absolute statistical certainties.
