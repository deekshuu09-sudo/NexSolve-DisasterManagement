# NexSolve Disaster Management System — Demonstration Runbook

This runbook provides step-by-step instructions for demonstrating the NexSolve Landslide Risk Intelligence Platform to evaluators, domain experts, and stakeholders.

---

## Pre-Demonstration Environment Setup

### 1. Start Backend API Server
```bash
# From workspace root directory
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
*Expected console output*:
```text
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 2. Verify Backend Readiness & Health Probes
```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/ready
```
*Expected response*:
- `/api/health`: `{"status": "ONLINE", "service": "NexSolve Risk Intelligence API", ...}`
- `/api/ready`: `{"status": "READY", "checks": {"model_loaded": true, "administrative_boundaries": true, ...}}`

### 3. Start Frontend Situation Room Dashboard
```bash
# In a separate terminal tab from frontend/
cd frontend
npm run dev
```
*Expected console output*:
```text
  VITE v5.x.x  ready in 150 ms
  ➜  Local:   http://localhost:5173/
```

---

## Guided Demonstration Steps

### Step 1: Open Dashboard & Review Header Warning Banners
1. Navigate browser to `http://localhost:5173/`.
2. Point out the **Header Warning Banner**:
   - `⚠️ PROTOTYPE / NON-OFFICIAL DISASTER MANAGEMENT SYSTEM`
   - Emphasize that NexSolve is an internal decision-support tool; official warnings require human SDMA/NDMA authorization.

### Step 2: System Situation Summary Bar (P9 Situation Room)
1. Highlight the 5 top-level situation awareness metrics cards:
   - **131 Monitored Districts** (Official Survey of India Boundaries).
   - **Weather Feed Health** (`LIVE` status across regional stations).
   - **High / Critical Risk Count** (Current active risk count).
   - **Vulnerability Coverage Summary** (Transparently showing 16/131 scored districts and 115 insufficient data districts).
   - **Road Corridor Watch** (NH-306, NH-2, NH-10, NH-6).

### Step 3: District Watchlist & Multi-Criterion Filters
1. Scroll to the **District Watchlist Table**.
2. Demonstrate multi-criterion filter dropdowns:
   - Filter by **State** (e.g., Mizoram, Manipur, Meghalaya).
   - Filter by **Risk Level** (`RED`, `ORANGE`, `YELLOW`, `GREEN`, `DATA UNAVAILABLE`).
   - Filter by **Vulnerability Coverage** (`COMPUTED`, `INSUFFICIENT_DATA`).
3. Select **Champhai District (Mizoram)** or **Senapati (Manipur)** by clicking `Inspect →`.

### Step 4: Interactive GIS Hazard & Corridor Map
1. Scroll to the **North Eastern Region (NER) Hazard Map**.
2. Switch layer toggles:
   - **All Layers** / **Risk Heatmap** / **Rainfall Intensity** / **Road Corridors**.
3. Click a district marker to show the Leaflet popup displaying official SoI LGD ID, DEM elevation/slope, and live weather provenance.

### Step 5: Explainable AI (XAI) Engine & Decision Support
1. Scroll to Section 03 (**Explainable AI Engine**).
2. Show the **Model-Level Feature Importance Breakdown**:
   - 24h Rain: 23.3%, 3d Rain: 22.9%, 7d Rain: 22.5%.
3. Point out the conservative non-causal explanation rationale (`Local Attribution: False`).

### Step 6: Decoupled Exposure & Vulnerability Panel (P7C)
1. Show the **Exposure & Vulnerability Card**:
   - Emphasize that **ML Risk ($P \in [0, 1]$) and Vulnerability Score ($S \in [0, 100]$) are 100% DECOUPLED** and NEVER multiplied.
   - Point out dataset reference years: UDISE+ Schools, MoHFW Hospitals, MoRTH Highways, NITI Aayog MPI.
2. Select a district with incomplete exposure data (e.g., Kamrup Metropolitan) to demonstrate that missing data displays **INSUFFICIENT DATA** with score `null` (never zero-filled).

### Step 7: Decision Support & Human Verification Checklist
1. Review the **4-Point Human Verification Protocol**:
   - Local weather station verification.
   - Ground observation report review.
   - Transport corridor & settlement exposure verification.
   - SDMA/NDMA human authorization requirement.

---

## Shutdown Procedure

1. Terminate Frontend: Press `CTRL+C` in the frontend terminal tab.
2. Terminate Backend: Press `CTRL+C` in the backend terminal tab.
