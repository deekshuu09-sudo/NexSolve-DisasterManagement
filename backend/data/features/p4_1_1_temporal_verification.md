# NexSolve — Phase 4.1.1 Final Temporal Leakage Verification Report

> [!IMPORTANT]
> **FINAL TEMPORAL VERDICT: YEAR-SAFE-ONLY**  
> Empirical inspection of `backend/services/feature_engineering_service.py` confirms the current inventory pipeline enforces **`event_year <= prediction_year`**. Exact day-level filtering (`event_date <= prediction_date`) across the 10,492 GSI inventory events is **BLOCKED BY SOURCE DATE RESOLUTION** because **79.7% of events (8,364 / 10,492)** in `ner_landslides.csv` contain ONLY the calendar year. Production ML model (`backend/model/landslide_model.pkl`) remains **100% UNCHANGED** (SHA-256: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`).

---

## 1. Inventory Date Fields & Temporal Resolution

Inspection of `backend/data/landslides/ner_landslides.csv` (10,492 rows):

- **Available Date Columns**: No dedicated `event_date` column exists. Date information resides in `slide_no` and `history`.
- **`history` Column**:
  - Null in **6,588 out of 10,492 rows (62.8% missing)**.
  - Contains parseable text for 3,904 rows (37.2%).
- **`slide_no` Column**: Contains 4-digit year tokens (e.g., `ASM/HKN/83D07/2020/2`) for **9,913 rows (94.5%)**.

### Breakdown of Source Temporal Resolution
| Temporal Resolution Category | Sample Examples from Source | Count of Events | Percentage |
| :--- | :--- | :-: | :-: |
| **`YEAR_ONLY`** | `ASM/HKN/83D07/2020/2`, `history = "2016"` | **8,364** | **79.7%** |
| **`EXACT_DATE`** | `history = "28 May 2024"`, `history = "17 May 2016"` | **1,400** | **13.3%** |
| **`MONTH_YEAR`** | `history = "July 2024"`, `history = "June 2025"` | **493** | **4.7%** |
| **`NO_TEMPORAL_INFO`** | `history` is null and `slide_no` has no year | **235** | **2.2%** |

> [!WARNING]
> **SOURCE DATA RESOLUTION LIMITATION**  
> For 79.7% of events, the Geological Survey of India (GSI) catalog records **ONLY the calendar year**. Day and month do NOT exist in the source data for 8,364 events.

---

## 2. Code Inspection & Execution Trace

### Exact File & Code Location
- File: [feature_engineering_service.py](file:///Users/deekshitharoy/Desktop/NexSolve-DisasterManagement/backend/services/feature_engineering_service.py#L71-L175)

### A. Year Extraction (`_init_spatial_indexes`)
```python
m = re.search(r'/(20\d\d)/', slide_no)
if m:
    yr = int(m.group(1))
```

### B. Current Temporal Cutoff Logic (`get_inventory_context`)
```python
prediction_year = None
if prediction_date:
    try:
        prediction_year = pd.to_datetime(prediction_date).year
    except Exception:
        pass

filtered_events = []
for e in INVENTORY_EVENTS:
    # 1. Temporal cutoff: event_year <= prediction_year
    if prediction_year is not None and e.get("year") is not None:
        if e["year"] > prediction_year:
            continue  # Excludes future years (e.g. 2025 excluded for 2024 sample)
```

---

## 3. Same-Year Contamination Analysis

> [!CAUTION]
> **CAN A LATER EVENT IN THE SAME YEAR CONTAMINATE AN EARLIER SAMPLE? YES.**

### Empirical Proof
When evaluating `get_inventory_context` for a point at `lat=24.5, lon=92.5`:
- `prediction_date = "2024-05-01"` $\rightarrow$ `prediction_year = 2024` $\rightarrow$ **9,994 eligible events**.
- `prediction_date = "2024-12-31"` $\rightarrow$ `prediction_year = 2024` $\rightarrow$ **9,994 eligible events**.

Because the filtering condition checks ONLY `e['year'] > prediction_year`:
- An inventory event occurring in **September 2024** has `year = 2024`.
- For a sample on **May 1, 2024**, `2024 > 2024` is `False`, so the September 2024 event is **NOT** filtered out.
- It enters `historical_event_count` and `event_density_per_sqkm`.

---

## 4. Target Event Exclusion Safety

In `get_inventory_context()`:
```python
if is_positive and prediction_year is not None:
    d_km = haversine_distance_km(lat, lon, e["lat"], e["lon"])
    if d_km < 0.05 and (e.get("year") == prediction_year or e.get("year") is None):
        continue
```

- **Positive Target Rows (`is_positive=True`)**: Excludes any co-located GSI inventory event within 50 meters occurring in `prediction_year`.
- **Control Rows (`is_positive=False`)**: Co-located events occurring in `prediction_year` are **NOT** excluded. If a control sample is taken on `2024-05-01` at a location where a landslide occurred in `September 2024`, the September event is included in the control sample's historical event count because `2024 <= 2024`.

---

## 5. Feasibility of Date-Level Filtering

1. **Full Exact Date Filtering**: **BLOCKED BY SOURCE RESOLUTION**. 8,364 out of 10,492 events (79.7%) in the GSI catalog lack day/month information.
2. **Hybrid Multi-Tier Date Filtering (Proposed Candidate Option)**:
   - For events with `EXACT_DATE` in `history` (1,400 events): enforce `event_date <= prediction_date`.
   - For events with `MONTH_YEAR` in `history` (493 events): enforce `event_month_end <= prediction_date`.
   - For events with `YEAR_ONLY` (8,364 events): apply conservative start-of-year bound (`YYYY-01-01 <= prediction_date`) or retain year-level cutoff.

---

## 6. Machine Learning Model Safety Audit

- **Artifact Path**: `backend/model/landslide_model.pkl`
- **SHA-256 Checksum**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`
- **Status**: **100% UNCHANGED & VERIFIED**.
