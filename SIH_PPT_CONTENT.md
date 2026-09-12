# NexSolve — SIH Presentation Deck Content (20-Slide Outline)

Judges' presentation deck content covering problem statement, scientific methodology, spatial framework, ML model performance, exposure intelligence, situation room dashboard, and governance.

---

### Slide 1: Title Slide
- **Title**: NexSolve — Enterprise Landslide Risk Intelligence & Decision Support Platform
- **Sub-Title**: Real-Time GIS Monitoring, Temporal ML Hazard Forecasting & Exposure Intelligence for Northeast India
- **Team**: Smart India Hackathon Team
- **Geographic Scope**: 8 Northeastern States | 131 Official Survey of India Districts

---

### Slide 2: Problem Statement
- **Headline**: Heavy Monsoons & Fragile Slope Geology Endanger Northeast India
- **Key Challenges**:
  1. Recurrent landslides disrupt arterial transport corridors (NH-306, NH-2, NH-10, NH-6).
  2. Isolated hill communities lack real-time rainfall-driven risk decision support.
  3. Existing approaches often lack data quality transparency or spatial boundary precision.

---

### Slide 3: NexSolve Solution Overview
- **Headline**: Data-Driven Decision Support for Disaster Management
- **Key Solution Pillars**:
  1. **Official Survey of India Boundaries**: 131 districts mapped with LGD identification.
  2. **Real-Time Weather Integration**: Live 1d, 3d, and 7d antecedent rainfall tracking with Open-Meteo feeds.
  3. **Promoted ML Engine**: Random Forest hazard classifier evaluated on temporal holdouts.
  4. **Decoupled Exposure Intelligence**: Domain-weighted socio-economic & critical asset exposure.
  5. **Operational Situation Room**: Multi-criterion watchlist, Leaflet GIS, and human verification protocols.

---

### Slide 4: System Architecture
- **Headline**: Microservice Architecture & Modular Intelligence Pipeline
- **Diagram**:
  - Data Layer: Weather Station Feeds, USGS/AWS 30m DEM, Survey of India GeoJSON, GSI Inventory.
  - Compute Layer: FastAPI Backend, Feature Engineering, Random Forest Predictor, Risk Decision Engine.
  - UI Layer: Vite/React 18 Situation Room Dashboard, Interactive OSM GIS Map, Human Verification Panel.

---

### Slide 5: Official Spatial Administrative Framework
- **Headline**: Survey of India ABDB LGD Integrated Geometry
- **Key Points**:
  - 8 Northeastern States (Arunachal Pradesh, Assam, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, Tripura).
  - 131 Official Districts forming primary administrative boundaries.
  - OpenStreetMap (OSM) serves as contextual base-map only; decision logic relies on official SoI boundaries.

---

### Slide 6: Terrain Intelligence & DEM Processing
- **Headline**: USGS / AWS Open Data Elevation Archive Integration
- **Key Points**:
  - NASADEM 1 Arc-Second (~30m SRTM DEM) tiles ingested and processed.
  - Spatial terrain statistics computed for all 131 districts: `elevation`, `slope`, `aspect`, `curvature`.
  - Terrain features provide environmental context and remain computationally separate from the ML prediction contract.

---

### Slide 7: Historical Landslide Baseline
- **Headline**: 10,492 Geological Survey of India (GSI) Records
- **Key Points**:
  - Historical inventory integrated across high-risk hill axes (Champhai, Senapati, Sohra, Tawang, Kohima).
  - Establishes spatial hazard density and historical occurrence baseline.

---

### Slide 8: Machine Learning Model & Feature Engineering
- **Headline**: Strict 7-Feature Leakage-Free Production Contract
- **Production Features**:
  1–2. `latitude`, `longitude` (Spatial coordinates)  
  3–5. `rainfall_1d`, `rainfall_3d`, `rainfall_7d` (Antecedent rainfall accumulation in mm)  
  6–7. `month_sin`, `month_cos` (Cyclical seasonality encoding)  
- **Model**: Promoted Random Forest Classifier (`candidate_a_rf_v1` v1.1.0, SHA `1acad34e85...`).

---

### Slide 9: Model Performance & Leakage Elimination
- **Headline**: Rigorous Temporal Holdout Evaluation
- **Benchmark Metrics**:
  - **ROC-AUC**: ~0.9206 | **PR-AUC**: ~0.9328
  - **Precision**: ~0.8312 | **Recall**: ~0.8204 | **F1**: ~0.8258
  - **Brier Score**: ~0.119 | **Calibration ECE**: ~0.059
- **Scientific Rigor**: Identified and eliminated earlier 0.99+ temporal leakage from random K-fold splits.

---

### Slide 10: Central Risk & Alert Decision Engine
- **Headline**: P6 Operational Decision Logic & Thresholds
- **Internal Prototype Thresholds**:
  - **Elevated Watch (YELLOW)**: Probabilities $\ge 0.35$ or 24h Rain $\ge 50$mm
  - **High Warning (ORANGE)**: Probabilities $\ge 0.50$ or 3d Rain $\ge 100$mm
  - **Critical Emergency (RED)**: Probabilities $\ge 0.75$ or 7d Rain $\ge 200$mm
- **Data Status**: `VERIFIED_LIVE`, `STALE`, or `DATA_UNAVAILABLE`.

---

### Slide 11: Weather Input Safety Gating (P0 Rule)
- **Headline**: Zero Guesswork When Weather Data Is Missing
- **Key Rules**:
  - Missing rainfall inputs gate risk to `DATA_UNAVAILABLE` (`risk_probability = null`).
  - Stale weather feeds downgrade confidence from `HIGH` to `MEDIUM`/`LOW` with `WEATHER_FEED_STALE` code.
  - Missing rainfall is **NEVER zero-filled**.

---

### Slide 12: Decoupled Exposure & Vulnerability Intelligence (P7C)
- **Headline**: 100% Separation of Hazard Risk and Exposure
- **5 Domains**: Demographic (Census), Healthcare (MoHFW), Schools (UDISE+), Transport Corridors (MoRTH), Socio-Economic MPI (NITI Aayog).
- **Decoupling Rule**: Risk $P \in [0, 1]$ and Vulnerability $S \in [0, 100]$ are displayed as separate cards and NEVER multiplied.

---

### Slide 13: Exposure Data Coverage Transparency
- **Headline**: Open Dataset Coverage Across 131 Districts
- **Current Coverage Breakdown**:
  - **8 Districts**: COMPUTED (Full 5-domain indicator coverage).
  - **8 Districts**: PARTIAL coverage.
  - **115 Districts**: INSUFFICIENT DATA (Composite score `null`, zero synthetic values).

---

### Slide 14: Explainability Engine (P8 XAI)
- **Headline**: Model-Level Interpretability & Feature Importances
- **Feature Importances**:
  - 24h Rain: 23.3% | 3d Rain: 22.9% | 7d Rain: 22.5% | Coordinates & Seasonality: ~31.3%
- **Governance**: `local_explanation_available = false` explicitly declared to avoid inventing unverified SHAP approximations.

---

### Slide 15: Operational Situation Room Dashboard (P9)
- **Headline**: High-Efficiency Interface for Decision-Makers
- **Key Features**:
  - Top Situation Summary Bar (131 Districts, Weather Health, High Risk Count, Vulnerability Coverage).
  - Watchlist Table with State, Risk Level, Weather Status, and Exposure Filters.
  - Interactive Leaflet GIS Map with Survey of India district boundaries and corridor overlays.

---

### Slide 16: Human-in-the-Loop Workflow
- **Headline**: Mandatory 4-Point Verification Checklist
- **Verification Protocol**:
  1. Confirm local station rainfall accumulation.
  2. Inspect crowd-sourced field observations.
  3. Inspect arterial highway corridors (NH-306, NH-2) and hospital exposure.
  4. Obtain human authorization from SDMA/NDMA officials.

---

### Slide 17: Containerization & Deployment Readiness (P10)
- **Headline**: Production-Ready Containerized Infrastructure
- **Deployment Artifacts**: Production `Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `.env.example`.
- **Readiness Probes**: Operational `GET /api/ready` endpoint verifying runtime model load, SHA-256 integrity, and Survey of India boundary files.

---

### Slide 18: Impact & Beneficiaries
- **Headline**: Operational Value for Disaster Management
- **Key Beneficiaries**:
  - State Disaster Management Authorities (SDMA / SDRF).
  - National Disaster Response Force (NDRF) Battalion Units.
  - District Administration & Public Works Departments (PWD / MoRTH).
  - Local Transport & Logistics Operators along NE corridors.

---

### Slide 19: System Limitations & Future Scope
- **Headline**: Transparent Boundary & Engineering Roadmap
- **Limitations**: Prototype decision-support status (`is_official_warning = false`); incomplete exposure coverage for 115 districts.
- **Future Scope**: Direct integration with IMD automatic weather station telemetry, expansion of local municipal exposure datasets, and automated SAR imagery processing.

---

### Slide 20: Closing Statement
- **Headline**: Science, Transparency, and Responsible AI for Disaster Resilience
- **Summary**: NexSolve combines spatial accuracy, temporal ML validation, data quality transparency, and human governance into a dependable decision-support platform for Northeast India.
- **Thank You!** | Questions & Jury Discussion
