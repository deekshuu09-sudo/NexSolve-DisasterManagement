# NexSolve Feature Status Matrix

This document defines the official scientific status, data provenance, temporal/spatial semantics, and ML eligibility for all **27 feature variables** in the NexSolve Disaster Management system.

---

## 1. Feature Status Matrix Summary Table

| # | Feature Name | Source Class | Static / Dynamic | Spatial Scale | Production Status | Experimental Status | Leakage Risk | Missing Value Policy | Notes |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | `sample_id` | OBSERVED | SNAPSHOT | POINT_EXACT | EXCLUDED | EXCLUDED | NONE | EXPLICIT_NULL | Key index |
| 2 | `latitude` | OBSERVED | STATIC | POINT_EXACT | **PRODUCTION** | APPROVED | NONE | EXPLICIT_NULL | WGS84 EPSG:4326 Lat |
| 3 | `longitude` | OBSERVED | STATIC | POINT_EXACT | **PRODUCTION** | APPROVED | NONE | EXPLICIT_NULL | WGS84 EPSG:4326 Lon |
| 4 | `date` | OBSERVED | SNAPSHOT | POINT_EXACT | EXCLUDED | EXCLUDED | NONE | EXPLICIT_NULL | YYYY-MM-DD date |
| 5 | `landslide` | OBSERVED | SNAPSHOT | POINT_EXACT | EXCLUDED | EXCLUDED | PROHIBITED | EXPLICIT_NULL | Target label (1 / 0) |
| 6 | `state_id` | DERIVED | STATIC | STATE_AGG | EXCLUDED | EXCLUDED | NONE | EXPLICIT_NULL | SOI State Code |
| 7 | `state_name` | DERIVED | STATIC | STATE_AGG | EXCLUDED | EXCLUDED | NONE | EXPLICIT_NULL | SOI State Name |
| 8 | `state_lgd` | DERIVED | STATIC | STATE_AGG | EXCLUDED | EXCLUDED | NONE | EXPLICIT_NULL | LGD State Code |
| 9 | `district_id` | DERIVED | STATIC | DISTRICT_AGG | EXCLUDED | EXCLUDED | NONE | EXPLICIT_NULL | SOI District Code |
| 10 | `district_name` | DERIVED | STATIC | DISTRICT_AGG | EXCLUDED | EXCLUDED | NONE | EXPLICIT_NULL | SOI District Name |
| 11 | `dist_lgd` | DERIVED | STATIC | DISTRICT_AGG | EXCLUDED | EXCLUDED | NONE | EXPLICIT_NULL | LGD District Code |
| 12 | `elevation_m` | OBSERVED | STATIC | POINT_EXACT | EXPERIMENTAL | APPROVED | NONE | EXPLICIT_NULL | NASADEM 30m Elev |
| 13 | `slope_deg` | DERIVED | STATIC | POINT_EXACT | EXPERIMENTAL | APPROVED | NONE | EXPLICIT_NULL | Sobel Slope (0-90°) |
| 14 | `aspect_deg` | DERIVED | STATIC | POINT_EXACT | EXPERIMENTAL | APPROVED | NONE | EXPLICIT_NULL | Aspect (0-360°, -1 flat) |
| 15 | `curvature` | DERIVED | STATIC | POINT_EXACT | EXPERIMENTAL | APPROVED | NONE | EXPLICIT_NULL | Laplacian Curvature |
| 16 | `terrain_quality` | DERIVED | STATIC | POINT_EXACT | EXPERIMENTAL | APPROVED | NONE | EXPLICIT_NULL | DEM Quality Tier |
| 17 | `district_mean_slope` | DERIVED | STATIC | DISTRICT_AGG | EXPERIMENTAL | APPROVED | NONE | EXPLICIT_NULL | Mean District Slope |
| 18 | `district_p90_slope` | DERIVED | STATIC | DISTRICT_AGG | EXPERIMENTAL | APPROVED | NONE | EXPLICIT_NULL | 90th Percentile Slope |
| 19 | `rainfall_1d` | OBSERVED | DYNAMIC_HIST | POINT_EXACT | **PRODUCTION** | APPROVED | NONE | EXPLICIT_NULL | 1-Day Rainfall (mm) |
| 20 | `rainfall_3d` | DERIVED | DYNAMIC_HIST | POINT_EXACT | **PRODUCTION** | APPROVED | NONE | EXPLICIT_NULL | 3-Day Rainfall (mm) |
| 21 | `rainfall_7d` | DERIVED | DYNAMIC_HIST | POINT_EXACT | **PRODUCTION** | APPROVED | NONE | EXPLICIT_NULL | 7-Day Rainfall (mm) |
| 22 | `month_sin` | DERIVED | SNAPSHOT | GLOBAL | **PRODUCTION** | APPROVED | NONE | EXPLICIT_NULL | Cyclical Month Sine |
| 23 | `month_cos` | DERIVED | SNAPSHOT | GLOBAL | **PRODUCTION** | APPROVED | NONE | EXPLICIT_NULL | Cyclical Month Cosine |
| 24 | `historical_event_count` | DERIVED | STATIC | DISTRICT_AGG | EXPERIMENTAL | APPROVED | MEDIUM | EXPLICIT_NULL | Temp-Cutoff Count |
| 25 | `event_density_per_sqkm` | DERIVED | STATIC | DISTRICT_AGG | EXPERIMENTAL | APPROVED | MEDIUM | EXPLICIT_NULL | Temp-Cutoff Density |
| 26 | `distance_to_nearest_event_km` | DERIVED | STATIC | POINT_EXACT | EXCLUDED | EXCLUDED | HIGH | EXPLICIT_NULL | Zero-variance (0.0km) |
| 27 | `soilSat` | SIMULATED | DYNAMIC_HIST | DISTRICT_AGG | EXCLUDED | EXCLUDED | PROHIBITED | EXPLICIT_NULL | UI Mock Proxy |

---

## 2. Status Category Definitions

- **OBSERVED**: Directly measured physical variable from authoritative remote sensing, weather stations, or official survey registries.
- **DERIVED**: Scientifically calculated variable derived from observed base fields using documented mathematical operators.
- **SIMULATED**: Synthetic or proxy value generated for visual or fallback purposes; strictly prohibited from ML training.
- **PRODUCTION**: Currently consumed by the production 7-feature Random Forest model (`backend/model/landslide_model.pkl`).
- **EXPERIMENTAL**: Approved candidate feature for future offline model evaluation (Phase 5).
- **EXCLUDED**: Explicitly prohibited from candidate ML feature sets due to zero variance, target leakage, or simulated proxy status.
