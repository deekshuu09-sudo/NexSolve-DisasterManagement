# NexSolve Scientific Validation Plan & Model Evaluation Rules

> [!CAUTION]
> **PROHIBITION OF RANDOM ROW SPLITTING**  
> Random row-level splitting ($k$-fold cross-validation or random train/test splits) is **STRICTLY PROHIBITED** for validating candidate ML models on this dataset.

---

## 1. Why Random Row-Level Splitting is Scientifically Invalid

The fused dataset utilizes a **temporal contrast sampling design**:
- **Positive Samples ($N=1,097$)**: Actual recorded landslide events at coordinates $(lat, lon)$ on event date $T_{event}$.
- **Control Samples ($N=1,097$)**: `CONTROL / NON-EVENT OBSERVATIONS` sampled at the **exact same location coordinates** $(lat, lon)$ on non-event dates $T_{control}$.

> [!WARNING]
> **CONTROL SAMPLE SEMANTICS**  
> Negative samples are **NOT** "confirmed non-landslides across the landscape". They are **CONTROL / NON-EVENT OBSERVATIONS** representing non-landslide dates at known landslide-susceptible locations.

Under a random row split:
1. The positive sample at $(lat, lon, T_{event})$ could be placed in the training set while its corresponding control sample at $(lat, lon, T_{control})$ is placed in the test set (or vice versa).
2. The ML estimator would memorize spatial features (`latitude`, `longitude`, `elevation_m`, `slope_deg`, `district_id`) and achieve artificially inflated accuracy ($>99\%$) due to spatial data leakage.

---

## 2. Mandatory Validation Strategies for Future ML Evaluation (Phase 5)

To ensure true physical generalization, all candidate ML models evaluated in Phase 5 must use one of the following 4 structured group-holdout strategies:

### Strategy A: Chronological Holdout
- **Training Partition**: Historical samples prior to 2024 ($Y \le 2023$).
- **Test Partition**: Samples from monsoon seasons 2024–2025.
- **Scientific Purpose**: Tests forecasting performance on future monsoon seasons using past historical observations.

### Strategy B: Location-Group Holdout
- **Grouping Key**: Unique spatial coordinate pair `(latitude, longitude)`.
- **Implementation**: `GroupKFold` split by `(latitude, longitude)` (1,097 location groups).
- **Scientific Purpose**: Ensures both positive and control samples for any location remain strictly in the same partition (train or test), preventing coordinate memorization.

### Strategy C: District-Group Holdout
- **Grouping Key**: Official Survey of India `district_id`.
- **Implementation**: `GroupKFold` grouped by `district_id` across 54 represented districts.
- **Scientific Purpose**: Evaluates how well terrain-rainfall physical risk thresholds generalize to completely unmonitored districts.

### Strategy D: Event-Aware Grouping
- **Grouping Key**: GSI Landslide Inventory `slide_no` or regional monsoon storm block.
- **Implementation**: `GroupKFold` grouped by storm event block.
- **Scientific Purpose**: Prevents samples triggered by the same regional cyclone or heavy rainstorm system from spanning train and test folds.
