# NexSolve Disaster Management System — SIH 2026 Prototype

> **GIS-based Landslide Risk Intelligence & Decision-Support System for the North Eastern Region of India (NER)**

NexSolve is an internal decision-support prototype developed for Smart India Hackathon (SIH) 2026. It integrates machine learning risk prediction, official Survey of India administrative boundaries, NASADEM terrain context, min-max normalized socio-economic exposure indicators, and human-in-the-loop decision rules.

---

## 📌 Overview

NexSolve provides disaster management authorities with structured risk assessment, spatial visualization, factor attribution, and standardized emergency decision brief generation across 8 North Eastern States (131 Districts).

**IMPORTANT**: NexSolve is an **internal prototype decision-support tool**. It is **NOT** a safety-critical operational early warning system or official government alert dispatch engine.

---

## 🏗️ System Architecture

```
                          ┌──────────────────────────────┐
                          │   React 18 + Leaflet GIS UI  │
                          │    (Vite / Tailwind / CSS)   │
                          └──────────────┬───────────────┘
                                         │ VITE_API_URL (HTTPS)
                                         ▼
                          ┌──────────────────────────────┐
                          │    FastAPI Risk Engine API   │
                          │   (Uvicorn / Python 3.11)    │
                          └──────────────┬───────────────┘
                                         │
        ┌──────────────────┬─────────────┴──────┬──────────────────┬──────────────────┐
        ▼                  ▼                    ▼                  ▼                  ▼
 ┌───────────────┐ ┌───────────────┐   ┌─────────────────┐ ┌───────────────┐  ┌───────────────┐
 │ Active RF ML  │ │ Open-Meteo REST│   │ Official SoI    │ │  NASADEM ~30m │  │ P7C Exposure  │
 │ Model (v1.1.0)│ │ Live Weather  │   │ Boundaries ABDB │ │ Terrain DEM   │  │ Profiles DB   │
 └───────────────┘ └───────────────┘   └─────────────────┘ └───────────────┘  └───────────────┘
```

---

## 🚀 Key Capabilities

1. **Active Machine Learning Risk Prediction**:
   - Random Forest model (`candidate_a_rf_v1.pkl`, SHA-256 verified) trained on spatial/temporal features.
   - Leakage-free 7-feature production input contract.
2. **Official Survey of India Spatial Governance**:
   - Integrated 131 SoI administrative district boundaries and 8 state boundaries.
   - Preserves official LGD district identifiers.
3. **P7C Decoupled Exposure & Vulnerability Intelligence**:
   - 5 domain indicators: Housing/Structural, Demographic, Healthcare, Transport, Education/Shelter.
   - Strict 100% computational separation from ML landslide risk prediction.
4. **P6 Risk Decision Engine**:
   - Categorizes risk decision levels: **RED** (Emergency $\ge 0.75$), **ORANGE** (Warning $\ge 0.50$), **YELLOW** (Elevated $\ge 0.35$), **GREEN** (Nominal $< 0.35$).
   - Returns explicit `DATA UNAVAILABLE` when live weather feeds are offline.
5. **P8 Explainability & Human-in-the-Loop Verification**:
   - Local factor decomposition and rationale notes.
   - Human verification checklists for authority evaluation.
6. **AI-Assisted Field Observations**:
   - Computer Vision image screening for field damage observations (in-memory verification).

---

## 🧠 ML Model & Production Feature Schema

- **Active Model Identifier**: `candidate_a_rf_v1`
- **Model Version**: `1.1.0`
- **Production Artifact SHA-256**: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1`
- **Candidate A Artifact SHA-256**: `1acad34e85b53df0cb68e5e81cd81d68066c4173792e65a51288b35557ba0f72`
- **7 Production Feature Contract**:
  1. `latitude` (Float, $-90.0$ to $+90.0$)
  2. `longitude` (Float, $-180.0$ to $+180.0$)
  3. `rainfall_1d` (24h accumulation, mm)
  4. `rainfall_3d` (3-day accumulation, mm)
  5. `rainfall_7d` (7-day accumulation, mm)
  6. `month_sin` ($\sin(2\pi \cdot \text{month} / 12)$)
  7. `month_cos` ($\cos(2\pi \cdot \text{month} / 12)$)

---

## 🗺️ Spatial & Terrain Integration

- **Survey of India ABDB**: Official spatial boundary boundaries for all 8 NER states and 131 districts.
- **NASADEM 1 Arc-Second (~30m SRTM DEM)**: Point and spatial terrain features (Elevation, Slope angle, Aspect, Curvature). Terrain parameters serve as analytical context and are **not** passed into the 7-feature RF model.

---

## 📊 Exposure & Vulnerability (P7C Framework)

- **Domain Coverage accounting**:
  - `FULL`: 5/5 domains available (8 operational locations: Champhai, Aizawl, Senapati, Sohra/East Khasi Hills, Tawang, Kohima, Dima Hasao, Dhalai).
  - `PARTIAL`: 3/5 domains available (1 operational location: Gangtok / East Sikkim).
  - `INSUFFICIENT`: 0 domains available (115 unacquired districts).
- **No Synthetic Zero-Filling**: Unacquired fields remain `null` / `UNAVAILABLE`.

---

## 💻 Local Development Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+

### 2. Backend Startup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Startup
```bash
cd frontend
npm install
npm run dev
```

The Vite dashboard will run at `http://localhost:5173`.

---

## ☁️ Cloud Deployment

See [DEPLOYMENT.md](file:///Users/deekshitharoy/Desktop/NexSolve-DisasterManagement/DEPLOYMENT.md) for detailed cloud deployment guides on Render (Backend Docker Container) and Vercel (Frontend Client).

---

## 🔒 Safety Controls & Disclaimers

1. **Non-Official Advisory**: NexSolve outputs are prototype decision-support briefs. They do not replace official India Meteorological Department (IMD) or State Disaster Management Authority (SDMA) warnings.
2. **Weather Safety Constraint**: When live weather feeds are unavailable, risk state transitions to `DATA UNAVAILABLE` without substituting historical data.
3. **No Automated Evacuation**: Automated siren dispatch or evacuation triggers are strictly forbidden. Human authority evaluation is mandatory.
