# NexSolve Disaster Management System — SIH 2026 Production Deployment Guide

This document specifies the deployment architecture, configuration parameters, environment variables, local execution commands, and production cloud deployment steps for the **NexSolve Disaster Management System** prototype.

---

## 1. System Architecture

```
                               ┌─────────────────────────────┐
                               │     Web Browser Client      │
                               │   (React + Vite + Leaflet)  │
                               └──────────────┬──────────────┘
                                              │ HTTPS API Requests
                                              ▼
                               ┌─────────────────────────────┐
                               │   Vercel Frontend Hosting   │
                               │   Static Dist Assets (CDN)  │
                               └──────────────┬──────────────┘
                                              │ VITE_API_URL
                                              ▼
                               ┌─────────────────────────────┐
                               │   Render FastAPI Backend    │
                               │  Uvicorn Service (Port $PORT)│
                               └──────────────┬──────────────┘
                                              │
         ┌───────────────────┬────────────────┼───────────────────┬───────────────────┐
         ▼                   ▼                ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌───────────┐ ┌───────────────────────┐ ┌───────────────────┐
│ Active RF Model │ │ Open-Meteo REST │ │  NASADEM  │ │ Survey of India ABDB  │ │    P7C Exposure   │
│ Candidate A v1  │ │ Weather Service │ │  ~30m DEM │ │ GeoJSON Boundaries    │ │ Domain Summaries  │
└─────────────────┘ └─────────────────┘ └───────────┘ └───────────────────────┘ └───────────────────┘
```

---

## 2. Required Environment Variables

### Frontend (`frontend/.env` or Vercel Environment Variables)
| Variable | Description | Example (Development) | Example (Production) |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | Base URL for FastAPI backend. | `http://127.0.0.1:8000` | `https://nexsolve-backend.onrender.com` |

### Backend (`backend/.env` or Render Environment Variables)
| Variable | Description | Example (Development) | Example (Production) |
| :--- | :--- | :--- | :--- |
| `HOST` | Binding host address. | `0.0.0.0` | `0.0.0.0` |
| `PORT` | Service binding port. | `8000` | Supplied by Render (`10000`) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins. | `http://localhost:5173,http://127.0.0.1:5173` | `https://nexsolve-frontend.vercel.app` |
| `FRONTEND_URL` | Primary production frontend origin. | `http://localhost:5173` | `https://nexsolve-frontend.vercel.app` |

---

## 3. Local Development Commands

### Backend Startup (FastAPI + Uvicorn)
```bash
# From workspace root
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Startup (Vite Dev Server)
```bash
# From frontend directory
cd frontend
npm run dev
```

---

## 4. Production Deployment Steps

### Step 1: Push Code to GitHub
Ensure all committed code is pushed to your GitHub repository:
```bash
git push origin main
```

### Step 2: Deploy Backend to Render
1. Log in to [Render Dashboard](https://dashboard.render.com/).
2. Select **New +** $\rightarrow$ **Web Service**.
3. Connect your GitHub repository: `deekshuu09-sudo/NexSolve-DisasterManagement`.
4. Choose **Docker** as the Environment / Runtime.
5. Set Root Directory: `./` (uses root `Dockerfile`).
6. Environment Variables:
   - `ALLOWED_ORIGINS`: `https://<your-vercel-frontend>.vercel.app`
7. Click **Create Web Service**.
8. Copy the generated backend service URL: `https://<backend-service-name>.onrender.com`.

### Step 3: Deploy Frontend to Vercel
1. Log in to [Vercel Dashboard](https://vercel.com/).
2. Select **Add New...** $\rightarrow$ **Project**.
3. Import repository: `deekshuu09-sudo/NexSolve-DisasterManagement`.
4. Set Root Directory: `frontend`.
5. Environment Variables:
   - `VITE_API_URL`: `https://<backend-service-name>.onrender.com`
6. Click **Deploy**.
7. Once deployed, copy the Vercel URL and add it to Render's `ALLOWED_ORIGINS` environment variable.

---

## 5. System Health Probes

- **Liveness Probe**: `GET /health` $\rightarrow$ `{"status": "ok"}`
- **API Status Probe**: `GET /api/health` $\rightarrow$ `{"status": "ONLINE"}`
- **Readiness Probe**: `GET /api/ready` $\rightarrow$ Verifies model loading and SoI administrative boundary readiness.

---

## 6. SIH Demo Disclaimers & Operational Limitations

1. **Decision-Support Scope**: NexSolve is an internal prototype / decision-support platform designed for SIH demonstration. It is **not** an official operational emergency warning system.
2. **Decoupled Risk & Vulnerability**: Modeled landslide risk probability (Random Forest) is strictly decoupled from P7C exposure/vulnerability scores.
3. **Live Weather Dependency**: If Open-Meteo external weather feeds are unreachable, risk prediction gracefully returns `DATA UNAVAILABLE / WEATHER FEED OFFLINE` without substituting historical data.
4. **Human Verification Contract**: All decision alerts require field verification by authorized SDMA/NDRF personnel prior to operational action.
