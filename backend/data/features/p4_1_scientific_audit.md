# NexSolve — Phase 4.1 Scientific & Data Integrity Audit Report (Hardened)

> [!IMPORTANT]
> **FINAL AUDIT VERDICT: PASS WITH LIMITATIONS**  
> All 26 feature columns in the canonical dataset (`backend/data/features/fused_feature_dataset.csv`) have **0% missing values** across 2,194 samples. Production Random Forest model (`backend/model/landslide_model.pkl`) remains **100% untouched** (SHA-256: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`). All backend unit tests (15/15 baseline + 12 scientific correction tests = 27 total tests) and frontend production build pass clean.

---

## 1. Executive Summary & Audit Hardening Highlights

Phase 4.1 performed an exhaustive scientific audit and feature-engineering hardening pass across the multi-modal dataset.

| Metric / Audit Check | Status / Result | Notes & Enforcement Details |
| :--- | :--- | :--- |
| **Audit Verdict** | **PASS WITH LIMITATIONS** | Scientific data integrity hardened; candidate feature sets updated. |
| **Dataset Completeness** | **100.0% (0 nulls)** | 2,194 rows × 26 columns = 57,044 cells with zero missing values. |
| **Production Model Safety** | **100% UNCHANGED** | SHA-256: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`. |
| **Production ML Feature Order** | **7 Features Preserved** | `[latitude, longitude, rainfall_1d, rainfall_3d, rainfall_7d, month_sin, month_cos]`. |
| **Distance Feature Status** | **EXCLUDED** | `distance_to_nearest_event_km` excluded from candidate set due to zero-variance ($0.0\text{ km}$). |
| **Aspect Semantics** | **VALIDATED** | Value `-1.0` validated as flat terrain / undefined aspect sentinel. |
| **DEM Provenance** | **CORRECTED** | SRTM 1 arc-second (~30m) via USGS / AWS Open Data Elevation Archive (Skadi S3). |
| **Temporal Leakage Control** | **HARDENED** | Enforced $Y_{event} \le Y_{sample}$ and target event exclusion on inventory features. |
| **Control Sample Semantics** | **CLASSIFIED** | Formally classified as `CONTROL / NON-EVENT OBSERVATIONS`. |
| **Validation Splitting Rules** | **HARDENED** | Random row splitting **PROHIBITED**; GroupKFold & Chronological holdouts mandated. |
| **Simulated `soilSat` Safeguard** | **PASSED** | Absent from dataset and ML predictor; strictly isolated to UI mock fallback. |

---

## 2. Comprehensive 26-Column Data Profiling Table

Below is the complete hardened profile for all 26 columns in `fused_feature_dataset.csv`.

| # | Column Name | Dtype | Missing % | Source Class | Temporal Meaning | Spatial Meaning | Leakage Risk | Min | Max | Mean | In Prod ML | Production Candidate |
| :-: | :--- | :--- | :-: | :---: | :---: | :---: | :---: | :-: | :-: | :-: | :-: | :-: |
| 1 | `sample_id` | int64 | 0.0% | OBSERVED | SNAPSHOT | POINT_EXACT | NONE | 1.0 | 2194.0 | 1097.5 | No | Excluded |
| 2 | `latitude` | float64 | 0.0% | OBSERVED | STATIC | POINT_EXACT | NONE | 22.4042 | 28.3892 | 24.2389 | **YES** | **Production** |
| 3 | `longitude` | float64 | 0.0% | OBSERVED | STATIC | POINT_EXACT | NONE | 88.1523 | 95.9278 | 92.6725 | **YES** | **Production** |
| 4 | `date` | object | 0.0% | OBSERVED | SNAPSHOT | POINT_EXACT | NONE | 2014-05-01 | 2025-09-01 | N/A | No | Excluded |
| 5 | `landslide` | int64 | 0.0% | OBSERVED | SNAPSHOT | POINT_EXACT | PROHIBITED | 0.0 | 1.0 | 0.5 | Target | Target |
| 6 | `state_id` | object | 0.0% | DERIVED | STATIC | STATE_AGG | NONE | N/A | N/A | N/A | No | Excluded |
| 7 | `state_name` | object | 0.0% | DERIVED | STATIC | STATE_AGG | NONE | N/A | N/A | N/A | No | Excluded |
| 8 | `state_lgd` | int64 | 0.0% | DERIVED | STATIC | STATE_AGG | NONE | 12.0 | 18.0 | 14.88 | No | Excluded |
| 9 | `district_id` | object | 0.0% | DERIVED | STATIC | DISTRICT_AGG | NONE | N/A | N/A | N/A | No | Excluded |
| 10 | `district_name` | object | 0.0% | DERIVED | STATIC | DISTRICT_AGG | NONE | N/A | N/A | N/A | No | Excluded |
| 11 | `dist_lgd` | int64 | 0.0% | DERIVED | STATIC | DISTRICT_AGG | NONE | 244.0 | 632.0 | 281.4 | No | Excluded |
| 12 | `elevation_m` | float64 | 0.0% | OBSERVED | STATIC | POINT_EXACT | NONE | 18.0 | 2976.0 | 664.1 | No | Experimental |
| 13 | `slope_deg` | float64 | 0.0% | DERIVED | STATIC | POINT_EXACT | NONE | 0.74 | 56.10 | 14.36 | No | Experimental |
| 14 | `aspect_deg` | float64 | 0.0% | DERIVED | STATIC | POINT_EXACT | NONE | 0.00 | 358.63 | 179.80 | No | Experimental |
| 15 | `curvature` | float64 | 0.0% | DERIVED | STATIC | POINT_EXACT | NONE | -1.2578 | 1.1875 | -0.0003 | No | Experimental |
| 16 | `terrain_quality` | object | 0.0% | DERIVED | STATIC | POINT_EXACT | NONE | N/A | N/A | N/A | No | Experimental |
| 17 | `district_mean_slope` | float64 | 0.0% | DERIVED | STATIC | DISTRICT_AGG | NONE | 0.45 | 24.89 | 12.45 | No | Experimental |
| 18 | `district_p90_slope` | float64 | 0.0% | DERIVED | STATIC | DISTRICT_AGG | NONE | 1.20 | 42.10 | 25.11 | No | Experimental |
| 19 | `rainfall_1d` | float64 | 0.0% | OBSERVED | DYNAMIC_HIST | POINT_EXACT | NONE | 0.0 | 485.4 | 28.72 | **YES** | **Production** |
| 20 | `rainfall_3d` | float64 | 0.0% | DERIVED | DYNAMIC_HIST | POINT_EXACT | NONE | 0.0 | 912.6 | 76.54 | **YES** | **Production** |
| 21 | `rainfall_7d` | float64 | 0.0% | DERIVED | DYNAMIC_HIST | POINT_EXACT | NONE | 0.0 | 1540.2 | 152.89 | **YES** | **Production** |
| 22 | `month_sin` | float64 | 0.0% | DERIVED | SNAPSHOT | GLOBAL | NONE | -1.0 | 1.0 | 0.0763 | **YES** | **Production** |
| 23 | `month_cos` | float64 | 0.0% | DERIVED | SNAPSHOT | GLOBAL | NONE | -1.0 | 1.0 | -0.5843 | **YES** | **Production** |
| 24 | `historical_event_count` | int64 | 0.0% | DERIVED | STATIC | DISTRICT_AGG | MEDIUM | 1.0 | 1025.0 | 511.25 | No | Experimental |
| 25 | `event_density_per_sqkm` | float64 | 0.0% | DERIVED | STATIC | DISTRICT_AGG | MEDIUM | 0.0003 | 0.7716 | 0.1302 | No | Experimental |
| 26 | `distance_to_nearest_event_km` | float64 | 0.0% | DERIVED | STATIC | POINT_EXACT | **HIGH** | 0.0 | 0.0 | 0.0 | No | **EXCLUDED** |

---

## 3. Provenance & Hardening Details

### A. DEM & Topography Provenance
- **Dataset**: SRTM 1 arc-second (~30m) global digital elevation data (USGS / SRTM1).
- **Acquisition Source**: USGS / AWS Open Data Elevation Archive (`https://elevation-tiles-prod.s3.amazonaws.com/skadi/`).
- **Archive Format**: $3601 \times 3601$ 16-bit signed big-endian integers (25,934,402 bytes per tile, uncompressed `.hgt`).
- **Tiles Acquired**: 90 contiguous tiles covering longitude `[88.0° E, 97.5° E]` and latitude `[21.0° N, 29.5° N]`.
- **CRS & NODATA**: WGS84 `EPSG:4326`, NODATA value `-32768`.

### B. Landslide Inventory & Temporal Leakage Control
- **Source**: Geological Survey of India (GSI) National Landslide Susceptibility Mapping (NLSM) 10,492 event catalog.
- **Row-Level Temporal Cutoff**: For a sample at prediction year $Y_{sample}$, only historical events with $Y_{event} \le Y_{sample}$ are included in inventory counts.
- **Target Event Exclusion**: For positive target samples, co-located target events ($d < 50\text{m}$) occurring in $Y_{sample}$ are strictly excluded.

### C. Control Sample Semantics & Validation Rules
- **Control Semantics**: Negative control samples represent non-landslide dates at known landslide coordinates (**CONTROL / NON-EVENT OBSERVATION**).
- **Validation Rule**: Random row splitting is **STRICTLY PROHIBITED**. Candidate models must be evaluated using GroupKFold by location/district or chronological holdouts.

---

## 4. Production Model Safety Audit

- **Artifact Path**: `backend/model/landslide_model.pkl`
- **SHA-256 Checksum**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`
- **Verification Status**: **100% UNCHANGED** (matches P0, P1, P2, P3, P4 baseline checksum).
- **Inference Feature Order**: `[latitude, longitude, rainfall_1d, rainfall_3d, rainfall_7d, month_sin, month_cos]`.
