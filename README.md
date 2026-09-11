# NexSolve — Real-Time Landslide Early Warning & Risk Platform

**High-End Real-Time Disaster Intelligence Engine for the North Eastern Region of India (NER)**

NexSolve is an enterprise-grade, real-time landslide hazard prediction, GIS mapping, and disaster readiness platform designed for high-vulnerability mountainous terrains.

---

## 🌟 Key Features & Design Architecture

1. **Ultra High-End Glassmorphism Dark Quartz Aesthetics**:
   - Palette: Obsidian Dark Zinc (`#030712`), Translucent Glass (`rgba(15, 23, 42, 0.75)`), Electric Cyan (`#06b6d4`), Cobalt Violet (`#6366f1`), and Emerald (`#10b981`).
   - Smooth `backdrop-filter: blur(20px)` panels with micro-glows.

2. **Aceternity UI & Motion.dev Design Implementations**:
   - **Aceternity Navbar Menu**: Floating rounded navbar container with smooth blur, translucent glass pills, and glowing active indicators.
   - **Aceternity Hover Border Gradient**: Conic-gradient rotating border animations on buttons (`.hover-border-btn`).
   - **Aceternity Background Boxes**: Interactive matrix grid background that highlights on mouse hover.
   - **Motion.dev Scroll Zoom Hero**: Smooth scale and zoom scroll interpolation on the hero text and coverage globe.

3. **Leaflet GIS Map with Esri World Dark Gray Engine**:
   - Uses Esri Dark Gray canvas tiles — **100% free, crisp, high-contrast, with NO API Key watermark**.
   - Features 5 layer toggles: *Risk Heatmap, Rainfall Radar, Priority Road Corridors, Relief Shelters, and SAR Satellite Deformation Vectors*.

4. **Explainable AI (XAI) Hazard Engine**:
   - Factor decomposition breakdown (*Rainfall 40%, Soil Moisture 25%, Slope Cut 20%, GSI History 15%*).
   - Interactive live simulators (+50mm Heavy Downpour, Dry Weather Recovery, Micro-Seismic Tremor).

5. **Crowdsourced CV Scanner & Multilingual Audio Warning**:
   - Computer Vision incident report modal with scan animation and confidence scoring.
   - Multilingual alert broadcast engine with 8 NER languages and Web Speech API Audio TTS.

6. **Full Backend Server & REST API**:
   - Node.js backend server (`server.js`) & Python backend server (`server.py`).
   - REST API Endpoints:
     - `GET /api/districts`: Returns real-time landslide risk matrix.
     - `GET /api/corridors`: Returns road corridor clearance status.
     - `POST /api/reports`: Ingests crowdsourced field reports with AI risk audit.
     - `GET /api/health`: Backend server health monitor.

---

## 🚀 How to Launch & Run

### Running with Python Backend
```bash
python3 server.py
```

### Running with Node.js Backend
```bash
node server.js
```

Open `http://localhost:8080` in your web browser.

## 🧠 Current ML/API integration status

The React dashboard now consumes the Python API for districts and road corridors. The API uses a transparent baseline risk scorer until a real labelled landslide dataset is supplied. This is intentional: NexSolve does not claim trained-model accuracy without spatial/temporal validation.

### Run the API locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Run the React dashboard
```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` to the local API by default. For a different API host, copy `frontend/.env.example` to `frontend/.env.local` and set `VITE_API_URL`.

## Production deployment

The active application is the React app in `frontend/` and the FastAPI app in `backend/main.py`. The root `app.js`, `index.html`, `server.js`, and `server.py` are legacy prototype files and are not deployment entry points for the current dashboard.

### Render backend

- Root Directory: repository root
- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Environment variable: `FRONTEND_URL=https://your-app.vercel.app`

Render must include the repository's `backend/model/landslide_model.pkl` and IMD NetCDF files under `backend/data/rainfall/`. The API uses repository-relative paths and does not require a database or local Mac path.

Health probes:

- `GET /health` returns `{"status":"ok"}`
- `GET /api/health` returns the existing detailed service status

### Vercel frontend

- Root Directory: `frontend`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment variable: `VITE_API_URL=https://your-api.onrender.com`

The frontend uses `VITE_API_URL` for all API requests. Do not put secrets in Vercel frontend variables; this value is a public API origin.

### Current ML and data status

The repository contains a Random Forest artifact and labelled training data used by the existing risk pipeline. The API reports `trained-random-forest` only when that artifact loads and the feature contract is satisfied; otherwise it uses the existing `transparent-baseline`. No accuracy claim is made by the deployment configuration. Image uploads are screened in memory and are not persisted by the current service.
