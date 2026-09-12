# P5.3 Model Calibration Report

## 1. Objective
To evaluate the calibration quality of probability estimates produced by Candidate A (`RF-LEAKAGE-FREE-BASELINE`) using strict pre-2024 fitting procedures and testing on the untouched 2024–2025 holdout ($Y \ge 2024$, 1,704 samples).

## 2. Calibration Methodology
- **Training Period**: `date <= 2023-12-31` (490 samples).
- **Calibration Method**: Sigmoid / Platt scaling via `CalibratedClassifierCV(method='sigmoid', cv=5)` fitted strictly on pre-2024 training data.
- **Test Set Independence**: Zero test labels ($Y \ge 2024$) were used during calibration fitting. Probabilities evaluated on the 2024–2025 holdout were strictly out-of-sample predictions.

## 3. Calibration Results

| Model Version | Calibration Method | Brier Score | ECE (Expected Calibration Error) | Max Bin Error |
|---|---|---|---|---|
| Candidate A (Uncalibrated Raw RF) | None (Raw Probabilities) | 0.1189 | 0.0586 | 0.1124 |
| Candidate A (Platt Sigmoid Calibrated) | Platt Sigmoid (CV=5 on Pre-2024) | 0.1207 | 0.0614 | 0.1285 |

## 4. Analysis & Discussion
- **Uncalibrated Raw Random Forest**: Achieves a Brier score of **0.1189** and an ECE of **0.0586**. The tree-ensemble output is well-calibrated natively owing to balanced class weighting (`class_weight='balanced'`) and 300-tree probability averaging.
- **Sigmoid Calibration Impact**: Applying Platt scaling on the small pre-2024 dataset (490 samples) slightly increased Brier score (0.1207) owing to small-sample estimation variance in fitting the sigmoid transformation parameters.
- **Operational Recommendation**: Raw probability outputs from Candidate A are preferred over post-hoc Sigmoid scaling due to native probability calibration stability. Probability scores should be interpreted as model confidence / risk scores rather than absolute statistical certainties.
