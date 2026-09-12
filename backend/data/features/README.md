# NexSolve Canonical Feature Engineering Architecture (P4)

This directory defines the canonical multi-modal feature engineering architecture for NexSolve, combining:
1. **Official Survey of India Administrative Boundaries** (`ner_states_soi.geojson`, `ner_districts_soi.geojson`)
2. **SRTM 1 Arc-Second (30m) Digital Elevation Models** (USGS / AWS Open Data Elevation archive `https://elevation-tiles-prod.s3.amazonaws.com/skadi/`)
3. **IMD Gridded Daily Rainfall Datasets** (1-day, 3-day, 7-day cumulative observations & forecast windows)
4. **Geological Survey of India (GSI) Historical Landslide Inventory** (`ner_landslides.csv`, 10,492 events)

---

## 1. Feature Architecture Overview

Features are categorized into five distinct layers:

### A. Static Terrain & Susceptibility
* `elevation_m`: Surface elevation in meters above mean sea level ($m$).
* `slope_deg`: Slope inclination angle ($0-90^\circ$) using 3x3 Sobel operator with latitude-scaled cell dimensions ($dx, dy$).
* `aspect_deg`: Steppest slope compass bearing ($0-360^\circ$). **Value `-1.0` is an explicit sentinel representing flat terrain (`slope == 0`) where aspect is mathematically undefined and MUST NOT be interpreted as a compass direction**.
* `curvature`: Profile Laplacian curvature ($m^{-2}$).
* `terrain_quality`: Provenance status (`"valid"`, `"nodata"`, `"unavailable"`).
* `district_mean_slope` / `district_p90_slope`: District-wide spatial terrain summary metrics.

### B. Dynamic Trigger & Rainfall
* `rainfall_1d`: 24-hour accumulated rainfall observation ($mm$).
* `rainfall_3d`: 3-day antecedent cumulative rainfall observation ($mm$).
* `rainfall_7d`: 7-day antecedent cumulative rainfall observation ($mm$).
* `month_sin` / `month_cos`: Seasonal cyclical transforms.

### C. Landslide Inventory & Historical Susceptibility
* `historical_event_count`: Total GSI historical events recorded in the district prior to prediction date ($Y_{event} \le Y_{sample}$, excluding target event).
* `event_density_per_sqkm`: Events per $\text{km}^2$ of official district area.
* `distance_to_nearest_event_km`: **STATUS: EXCLUDED FROM CANDIDATE FEATURE SET**. Zero-variance feature ($0.0 \text{ km}$) due to temporal contrast sampling design (pairing non-event dates at historical event locations). Retained in fused CSV strictly for audit/provenance.

### D. Administrative & Infrastructure Exposure
* `state_id`, `state_lgd`: Official LGD state identifier.
* `district_id`, `dist_lgd`: Official LGD district identifier.

### E. Target & Sample Semantics
* `landslide`: Binary target variable (`1` = Landslide occurrence, `0` = Control / Non-event observation).
* **Control Sample Semantics**: Negative samples are **CONTROL / NON-EVENT OBSERVATIONS** (dates with no recorded landslide at known landslide location coordinates), NOT confirmed non-landslide points across the landscape.

---

## 2. Machine Learning Safety & Model Isolation

> [!IMPORTANT]
> The current production Random Forest predictor (`backend/model/landslide_model.pkl`) relies strictly on 7 features:
> `["latitude", "longitude", "rainfall_1d", "rainfall_3d", "rainfall_7d", "month_sin", "month_cos"]`.
> 
> **P4 is a feature alignment & data hardening phase**. No terrain or inventory features are fed into the production predictor model, and `landslide_model.pkl` is **not retrained or modified** (SHA-256 `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`).

---

## 3. Data Provenance Verification

* **Administrative Boundaries**: Survey of India ABDB (`State_District_Subdistrict_PAN_INDIA.rar`, SHA-256 `b8325e5d9dd0f04a6663d775363fe38cd2f23bd9dbae3fb7118b4e6e0ce0bcb7`).
* **DEM Elevation Grid**: SRTM 1 arc-second (~30m) elevation data via USGS / AWS Open Data Elevation Archive (`https://elevation-tiles-prod.s3.amazonaws.com/skadi/`, 90 tiles, $3601 \times 3601$ int16 HGT raster grids).
* **Rainfall Feed**: IMD High-Resolution Gridded Daily Rainfall NetCDF Archive & Live Weather Feed.
* **Landslide Inventory**: Geological Survey of India (GSI) 10,492 event catalog.
