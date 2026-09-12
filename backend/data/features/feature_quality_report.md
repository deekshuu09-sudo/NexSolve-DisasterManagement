# NexSolve Feature Engineering Dataset Quality Report (P4)

## 1. Dataset Summary
- **Total Samples**: 2194
- **Class Balance**: 1,097 Positive (`landslide = 1`), 1,097 Negative Control (`landslide = 0`)
- **Spatial Assignment**: 2194 / 2194 samples spatially assigned to official Survey of India ABDB districts.

## 2. Terrain Metrics Integrity (NASADEM 30m)
- **Valid Elevation Count**: 2194 samples (100.0%)
- **Elevation Range**: 18.0 m to 2976.0 m
- **Slope Range**: 0.74° to 56.1°

## 3. Rainfall Consistency
- **Monotonicity Check (`rainfall_1d` <= `rainfall_3d` <= `rainfall_7d`)**: **PASS** (0 violations)

## 4. Leakage Controls
- **Temporal Leakage Violations**: 0
- **Target Exclusion in Inventory Metrics**: Enforced
- **Production ML Predictor Artifact**: Untouched (SHA-256 `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`)
