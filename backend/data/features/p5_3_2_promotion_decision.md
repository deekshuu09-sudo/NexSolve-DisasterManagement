# P5.3.2 Promotion Decision Document

## 1. Executive Summary
- **Current Production Model Artifact**: `backend/model/landslide_model.pkl`
- **Current Production Model SHA-256**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1` (**100% UNCHANGED**)
- **Selected Candidate Model**: Candidate A (`candidate_a_rf_v1_2.pkl` stored in `backend/model/experimental/`)
- **Leakage-Free Temporal ROC-AUC**: **0.9206**
- **Leakage-Free Temporal PR-AUC**: **0.9328**
- **F1 Score (t=0.50)**: **0.8258**
- **Brier Score**: **0.1195**
- **ECE**: **0.0624**
- **Location-Group CV ROC-AUC**: **0.9644**
- **District-Group CV ROC-AUC**: **0.9347**

## 2. Formal Promotion Decision

**CANDIDATE-READY-FOR-PROMOTION-REVIEW**

## 3. Justification & Rationale
1. **Contamination Elimination**: Candidate A was trained strictly on pre-2024 development data ($Y \le 2023$, 490 samples), successfully eliminating the 2024+ training contamination present in the original production artifact (which had been trained through May 2025).
2. **Superior Temporal Generalisation**: Candidate A achieved ROC-AUC **0.9206** on the locked 2024–2025 holdout, outperforming terrain-enhanced Candidate B (0.9148) and inventory-enhanced Candidate C (0.8912).
3. **No Overwrite Control**: The production model artifact `landslide_model.pkl` was **NOT overwritten**. Candidate A is stored as a versioned candidate artifact in `backend/model/experimental/candidate_a_rf_v1_2.pkl`.
4. **Conservative Promotion Safeguard**: Formal promotion review by human domain experts is required before deploying Candidate A to replace the production artifact.

## 4. Key Limitations & Operational Disclaimers
- **Spatial Concentration**: Mizoram represents 75.7% of evaluation samples in the locked test set (1,290 / 1,704 samples).
- **Unrepresented Districts**: 77 of 131 official Survey of India districts currently lack historical evaluation samples.
- **Prototype Risk Thresholds**: Thresholds (0.35 / 0.50) are prototype decision-support thresholds requiring domain/expert validation — NOT official government alert thresholds.
