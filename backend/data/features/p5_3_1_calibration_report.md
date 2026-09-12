# P5.3.1 Leakage-Safe Model Calibration Report

## 1. Objective
To document the calibration quality of probability estimates produced by Candidate A (`RF-LEAKAGE-FREE-BASELINE`) under strict temporal leakage controls, ensuring calibration parameters were learned **exclusively** from pre-2024 development data ($Y \le 2023$, 490 samples) before evaluating on the locked 2024–2025 holdout ($Y \ge 2024$, 1,704 samples).

## 2. Calibration Fitting Protocol
- **Development Dataset**: `date <= 2023-12-31` (490 samples: 245 positive, 245 control).
- **Calibration Method**: Sigmoid / Platt scaling fitted via `CalibratedClassifierCV(method='sigmoid', cv=5)` strictly on pre-2024 development data.
- **Holdout Locking Verification**: Zero labels or predictions from the 2024–2025 holdout ($Y \ge 2024$) were accessed or used during calibration fitting. The calibrated transformation was frozen before final evaluation.

## 3. Calibration Evaluation on Locked 2024–2025 Holdout

| Model Version | Calibration Fitting Dataset | Evaluation Holdout | Brier Score | ECE (Expected Calibration Error) | Max Bin Calibration Error |
|---|---|---|---|---|---|
| Candidate A (Uncalibrated Raw RF) | None (Raw Ensemble Output) | Locked 2024–2025 Holdout | 0.1189 | 0.0586 | 0.1124 |
| Candidate A (Platt Sigmoid Calibrated) | Pre-2024 Dev Data ($Y \le 2023$) | Locked 2024–2025 Holdout | 0.1207 | 0.0614 | 0.1285 |

## 4. Key Findings
- **Uncalibrated Probability Quality**: Uncalibrated probabilities natively from Candidate A achieved a Brier score of **0.1189** and an ECE of **0.0586**. Class-balanced sampling (`class_weight='balanced'`) and 300-tree probability averaging provide robust native calibration.
- **Sigmoid Scaling Impact**: Fitting Platt Sigmoid scaling on the smaller pre-2024 dataset (490 samples) slightly increased Brier score (0.1207) owing to small-sample estimation variance in fitting the transformation curve.
- **Operational Recommendation**: Raw ensemble probabilities from Candidate A are recommended over post-hoc Sigmoid scaling. Outputs must be presented as risk confidence scores rather than absolute statistical certainties.
