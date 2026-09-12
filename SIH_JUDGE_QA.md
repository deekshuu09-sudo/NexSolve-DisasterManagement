# NexSolve — Smart India Hackathon (SIH) Judge Q&A Guide

Comprehensive answers for domain experts, technical evaluators, and jury members.

---

### Q1: What problem is NexSolve solving?
**Answer**:  
NexSolve provides real-time landslide risk intelligence and decision-support for the 8 Northeastern States of India. Mountainous terrain, heavy monsoon rainfall, and fragile geology cause frequent landslides that block strategic highway corridors (e.g., NH-306, NH-2) and endanger hilltop communities. NexSolve synthesizes weather station feeds, spatial administrative boundaries, machine learning hazard risk, open exposure datasets, and explainable decision support into an operational situation room.

---

### Q2: Is NexSolve an official government early warning system?
**Answer**:  
No. NexSolve is strictly an **internal decision-support prototype** for disaster-management personnel. It does NOT possess official warning authority, issue public evacuation orders, or replace State/National Disaster Management Authorities (SDMA/NDMA). All API responses hardcode `is_official_warning = false`.

---

### Q3: What datasets are used in the project?
**Answer**:
1. **Administrative Boundaries**: Official Survey of India (ABDB LGD Integrated) GeoJSON boundaries covering 8 NE States and 131 official districts.
2. **Landslide History**: 10,492 historical Geological Survey of India (GSI) inventory records.
3. **Terrain Elevation**: USGS / AWS Open Data Elevation Archive (NASADEM 1 Arc-Second ~30m SRTM DEM) processed into district-level elevation, slope, aspect, and curvature metrics.
4. **Weather Feeds**: Open-Meteo real-time/hourly precipitation API feeds with historical IMD grid fallbacks.
5. **Exposure Intelligence**: Open government datasets including UDISE+ schools, MoHFW healthcare facilities, MoRTH arterial highways, and NITI Aayog Multidimensional Poverty Index (MPI).

---

### Q4: What machine learning model is deployed, and what features does it use?
**Answer**:  
We use a promoted **Random Forest Classifier** (`candidate_a_rf_v1` v1.1.0) operating on a strict **7-feature production contract**:
1. `latitude` (Decimal degrees)
2. `longitude` (Decimal degrees)
3. `rainfall_1d` (24-hour antecedent rainfall in mm)
4. `rainfall_3d` (3-day cumulative rainfall in mm)
5. `rainfall_7d` (7-day cumulative rainfall in mm)
6. `month_sin` ($\sin(2\pi \cdot \text{month}/12)$ for seasonality)
7. `month_cos` ($\cos(2\pi \cdot \text{month}/12)$ for seasonality)

Zero leakage features (such as same-day triggers or target proxies) are included.

---

### Q5: How reliable is the ML model, and how did you validate it?
**Answer**:  
The model was evaluated on an **uncontaminated temporally separated holdout dataset**, achieving:
- **ROC-AUC**: ~0.9206
- **PR-AUC**: ~0.9328
- **Precision**: ~0.8312
- **Recall**: ~0.8204
- **F1 Score**: ~0.8258
- **Brier Score**: ~0.119
- **Expected Calibration Error (ECE)**: ~0.059 – 0.062

---

### Q6: Why did you discard the earlier 0.99+ ROC-AUC performance metric?
**Answer**:  
During audit phase P5.3, we discovered that earlier cross-validation models suffered from **temporal data leakage** because random K-fold splits mixed data from the same monsoon events across training and validation folds. We identified and eliminated this leakage by implementing strict temporal splitting, establishing the true un-contaminated benchmark of ~0.9206 ROC-AUC.

---

### Q7: Why are terrain features (slope, aspect) not included in the ML feature contract?
**Answer**:  
To prevent model overfitting on static spatial coordinates and maintain a clean 7-feature rainfall/seasonality prediction contract. Terrain features derived from the 30m DEM are displayed alongside ML risk in the UI to provide environmental decision context for disaster managers, but are kept computationally separate from model inference.

---

### Q8: How does NexSolve handle missing or unavailable weather data?
**Answer**:  
NexSolve enforces strict **Data Availability Gating (P0 Safety Rule)**: if live rainfall data is missing or unavailable, the system refuses to guess or invent values. It returns `risk_probability = null`, `risk_level = "DATA_UNAVAILABLE"`, `confidence = "UNAVAILABLE"`, and decision status `NOT_EVALUABLE`. Missing rainfall is NEVER zero-filled.

---

### Q9: How does the system handle stale weather data?
**Answer**:  
If weather data is received but marked stale (e.g., station update delayed >3 hours), the system evaluates risk but automatically downgrades confidence from `HIGH` to `MEDIUM` or `LOW` and attaches reason code `WEATHER_FEED_STALE`.

---

### Q10: Are the decision thresholds (0.35, 0.50, 0.75) official government alert levels?
**Answer**:  
No. The thresholds (`0.35` Elevated/Yellow, `0.50` Warning/Orange, `0.75` Emergency/Red) are **internal prototype thresholds** established during candidate operating point analysis. They are clearly labeled as prototype decision-support markers.

---

### Q11: Why are ML Landslide Risk and Vulnerability Scores kept separate?
**Answer**:  
Landslide Hazard Risk ($P \in [0, 1]$) measures the physical probability of a landslide occurring based on rainfall and seasonality. Vulnerability ($S \in [0, 100]$) measures socio-economic exposure (healthcare, schools, highways, poverty). Combining or multiplying $P \times S$ creates a mathematically flawed composite number that obscures physical hazard. NexSolve displays them as two distinct, transparent information cards.

---

### Q12: Are exposure and vulnerability data available for all 131 districts?
**Answer**:  
No. While NexSolve maintains a 131-district official Survey of India administrative framework, open exposure data is available at varying levels. Currently, 16 districts have scored vulnerability profiles (8 COMPUTED with full 5-domain coverage, 8 PARTIAL); 115 districts remain `INSUFFICIENT_DATA` with composite score `null`. Missing data is transparently flagged rather than zero-filled.

---

### Q13: How is Explainability (XAI) implemented?
**Answer**:  
NexSolve provides **Model-Level Feature Importance** derived from the Random Forest classifier (24h rain: 23.3%, 3d rain: 22.9%, 7d rain: 22.5%, coordinates/seasonality: ~31.3%). We explicitly set `local_explanation_available = false` to avoid inventing unverified local SHAP/LIME approximations.

---

### Q14: Is NexSolve deployed live in the cloud?
**Answer**:  
Containerized deployment configuration is prepared (`Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `GET /api/ready`). Public cloud deployment status is recorded as `PUBLIC_CLOUD_DEPLOYMENT: NOT_VERIFIED` because live cloud hosting requires evaluator cloud credentials.

---

### Q15: What is the role of human personnel in NexSolve?
**Answer**:  
NexSolve enforces a **Human-in-the-Loop Workflow**. Before taking any operational action, disaster-management personnel must complete a 4-point verification checklist:
1. Verify local station rainfall accumulation.
2. Inspect crowd-sourced field observations.
3. Check exposed road corridors and critical infrastructure.
4. Confirm decisions with authorized SDMA/NDMA disaster management authorities.
