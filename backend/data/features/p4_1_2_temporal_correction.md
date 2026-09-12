# NexSolve — Phase 4.1.2 Multi-Tier Temporal & Target Exclusion Audit

> [!IMPORTANT]
> **FINAL VERDICT: TEMPORALLY-SAFE-TO-SOURCE-RESOLUTION**  
> **MODEL: UNCHANGED**  
> Feature engineering enforces multi-tier temporal cutoffs matching the highest resolution provided by the Geological Survey of India (GSI) source catalog. Exact-date records are date-level safe; month-year records are month-level safe; year-only records are year-level safe; events lacking temporal information are excluded. Target exclusion uses spatial distance matching ($d < 50\text{m}$) because training samples lack explicit inventory foreign keys. Production Random Forest model (`backend/model/landslide_model.pkl`) remains **100% UNCHANGED** (SHA-256: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`).

---

## 1. Multi-Tier Temporal Resolution Semantics & Audit

| Temporal Tier | Source Representation | Event Count | Percentage | Code Filtering Rule | Temporal Safety Level |
| :--- | :--- | :-: | :-: | :--- | :--- |
| **`EXACT_DATE`** | Day, month, and year present in `history` (e.g. `"28 May 2024"`, `"17 May 2016"`) | **1,428** | **13.6%** | `exact_date <= prediction_date` | **DATE-LEVEL SAFE** |
| **`MONTH_YEAR`** | Month and year present in `history` (e.g. `"July 2024"`, `"June 2025"`) | **440** | **4.2%** | `(event_year < pred_year) or (event_year == pred_year and event_month <= pred_month)` | **MONTH-LEVEL SAFE ONLY** |
| **`YEAR_ONLY`** | Year in `slide_no` (e.g. `ASM/HKN/83D07/2020/2`) or `history` (e.g. `"2016"`) | **8,389** | **79.9%** | `event_year <= prediction_year` | **YEAR-LEVEL SAFE ONLY** |
| **`NO_TEMPORAL_INFO`** | Missing history text and `slide_no` year | **235** | **2.2%** | **EXCLUDED** from time-dependent features | **NOT INCLUDED** |

> [!WARNING]
> **MONTH/YEAR TEMPORAL LIMITATION**  
> `MONTH_YEAR` records are **NOT day-level safe**. For example, if a sample is dated `2024-05-01` and an inventory event is recorded as `May 2024` without a day, it cannot be proven whether the event occurred before or after May 1. No synthetic day (e.g., first or last day of month) is invented; the tier is described strictly as **MONTH-LEVEL TEMPORAL RESOLUTION**.

---

## 2. Target Event Exclusion Audit & Spatial Matching

### A. Source Event Identification
- **Catalog Identifiers**: `ner_landslides.csv` contains unique event keys `serial_no` (integer 1..10492) and `slide_no` (string e.g. `ASM/HKN/83D07/2020/2`).
- **Sample Key Availability**: Training samples in `ml_dataset.csv` / `fused_feature_dataset.csv` store coordinates (`latitude`, `longitude`) and sample date (`date`), but **do NOT store `serial_no` or `slide_no` foreign keys**.

### B. Exclusion Mechanism Implemented
Because foreign keys are absent in training samples, target exclusion for positive samples (`is_positive=True`) is performed via **spatial distance matching**:
```python
if is_positive and pred_year is not None:
    d_km = haversine_distance_km(lat, lon, e["lat"], e["lon"])
    if d_km < 0.05 and (e.get("year") == pred_year or e.get("year") is None):
        continue
```

### C. What Spatial Distance Exclusion Guarantees vs. What it Does NOT Guarantee
- **Guarantees**: Guarantees that any GSI inventory event within 50 meters of the positive sample coordinate occurring in `prediction_year` (or missing year) is excluded from `historical_event_count` and `event_density_per_sqkm`, preventing self-inclusion of the target event.
- **Does NOT Guarantee**:
  1. Does NOT guarantee unique event identity matching if multiple distinct landslides occurred within 50 meters during the same calendar year (unrelated events within 50m in the same year are also excluded).
  2. Does NOT exclude target events if the spatial coordinate mismatch between the sample and the catalog record exceeds 50 meters ($d > 50\text{m}$).

---

## 3. Machine Learning Safety & Model Integrity

- **Model Artifact**: `backend/model/landslide_model.pkl`
- **SHA-256 Checksum**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`
- **Status**: **100% UNCHANGED & VERIFIED IDENTICAL**.
- **Production Feature Order**: `[latitude, longitude, rainfall_1d, rainfall_3d, rainfall_7d, month_sin, month_cos]`.
