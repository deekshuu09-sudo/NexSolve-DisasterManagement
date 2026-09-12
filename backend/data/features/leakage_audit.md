# NexSolve P4 Temporal & Spatial Leakage Audit

## 1. Objective & Audit Scope
This audit documents the controls implemented in P4 & P4.1 to prevent information leakage across feature engineering, training datasets, and spatial-temporal evaluation splits.

---

## 2. Leakage Verification Matrix

| Feature Category | Feature Name | Leakage Risk | Control & Enforcement Mechanism | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Static Terrain** | `elevation_m`, `slope_deg`, `aspect_deg`, `curvature` | **Low** | Derived from pre-event 30m DEM grids. Represents permanent geomorphology. Aspect `-1.0` = flat sentinel. | **PASS** |
| **Dynamic Rainfall** | `rainfall_1d`, `rainfall_3d`, `rainfall_7d` | **High** | Strictly computed from 24h, 3-day, and 7-day windows ending **on or before** the prediction date $T$. Post-event rainfall is strictly excluded. | **PASS** |
| **Seasonal Cyclical** | `month_sin`, `month_cos` | **None** | Computed deterministically from prediction date $T$. | **PASS** |
| **Inventory Context** | `historical_event_count`, `event_density_per_sqkm` | **Medium** | Enforces row-level temporal cutoff ($Y_{event} \le Y_{sample}$) AND target event exclusion ($d > 50\text{m}$ for positive samples). Future events ($Y > Y_{sample}$) are excluded. | **HARDENED & PASS** |
| **Distance Feature** | `distance_to_nearest_event_km` | **High / Zero-Var** | **EXCLUDED FROM CANDIDATE FEATURE SET**. Collapses to $0.0\text{ km}$ due to temporal contrast sampling at identical spatial coordinates. | **EXCLUDED** |
| **Target Label** | `landslide` | **Critical** | Ground truth label (`1` / `0`) is isolated from predictor feature arrays. Control samples represent non-event dates at landslide coordinates. | **PASS** |
| **Simulated Proxy** | `soilSat` | **Prohibited** | Simulated soil saturation is strictly isolated to UI mock fallbacks and prohibited from ML feature sets. | **EXCLUDED** |

---

## 3. Key Leakage Audit Findings

1. **Target Event & Future Event Exclusion (Hardened in P4.1)**:
   - When calculating `historical_event_count` or `event_density_per_sqkm` for a sample at date $T$, ONLY GSI inventory events with $Y_{event} \le Y_{sample}$ are included.
   - Future events occurring after prediction date $T$ are strictly filtered out ($Y_{event} > Y_{sample}$ excluded).
   - For positive target samples, the co-located target event itself is excluded from the historical count.

2. **Distance Feature Exclusion (`distance_to_nearest_event_km`)**:
   - Because temporal contrast sampling selects control samples at the exact same location coordinates $(lat, lon)$ as historical positive events, `distance_to_nearest_event_km` is identically $0.0\text{ km}$ for all samples.
   - This feature has been formally **EXCLUDED** from production and experimental candidate schemas (`status = EXCLUDED`, `reason = ZERO_VARIANCE_DUE_TO_SAMPLING_DESIGN`).

3. **Production Model Safety**:
   - The production Random Forest classifier (`backend/model/landslide_model.pkl`) remains strictly isolated to its original 7 features (`latitude`, `longitude`, `rainfall_1d`, `rainfall_3d`, `rainfall_7d`, `month_sin`, `month_cos`). SHA-256 hash `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1` is 100% preserved.
