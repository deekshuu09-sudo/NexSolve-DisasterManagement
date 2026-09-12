# NexSolve — SIH Demonstration Script (5–7 Minutes)

**Target Audience**: Smart India Hackathon (SIH) Judges, Domain Experts & Disaster Management Evaluators  
**Demonstrator Role**: Lead System Architect & AI Engineer  
**System Scope**: SIH Decision-Support Prototype for Landslide Risk Intelligence in Northeast India  

---

## Demonstration Setup Checklist

- [ ] Backend API running: `python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
- [ ] Frontend running: `http://localhost:5173/`
- [ ] Browser zoom set to 100%, fullscreen dark theme.
- [ ] Disclaimer note ready: *"Demonstration scenario — for decision-support evaluation."*

---

## Script Walkthrough (7 Key Steps)

### Step 1: Introduction & Problem Context (0:00 – 1:00)
> **Demonstrator**:  
> *"Good morning, respected judges. We present **NexSolve** — an enterprise decision-support prototype for landslide risk intelligence tailored for the 8 North Eastern States of India.*  
> *Landslides in the Northeast disrupt vital arterial transport corridors, isolate remote communities, and cause catastrophic slope failures during monsoon seasons. Current approaches often lack real-time rainfall data integration, spatial administrative mapping, or data quality transparency.*  
> *NexSolve bridges this gap by combining official Survey of India administrative boundaries, real-time weather feeds, temporal ML risk modeling, exposure intelligence, and explainable AI into a single Operational Situation Room."*

---

### Step 2: System Situation Room & Geographic Framework (1:00 – 2:00)
> **Demonstrator**:  
> *(Point to the top header and situation summary bar on `http://localhost:5173/`)*  
> *"Notice first our strict commitment to safety: prominently rendered banners emphasize that NexSolve is an internal decision-support prototype. Official public warning authority remains strictly with SDMA and NDMA.*  
> *Our spatial framework is built on **131 Official Survey of India (ABDB LGD Integrated) District Boundaries** across all 8 Northeastern states.*  
> *The Top Situation Summary Bar provides instant operational awareness: tracking 131 monitored districts, live weather feed health, high/critical risk counts, vulnerability data coverage, and priority road corridors."*

---

### Step 3: District Watchlist & Multi-Criterion Filtering (2:00 – 3:00)
> **Demonstrator**:  
> *(Scroll to the District Watchlist Table)*  
> *"In a disaster management situation room, decision-makers cannot search blindly. NexSolve provides multi-criterion watchlist filters.*  
> *We can filter districts by **State**, **Risk Level** (RED, ORANGE, YELLOW, GREEN, DATA UNAVAILABLE), **Weather Health**, and **Vulnerability Data Availability**.*  
> *Let me select **Champhai District (Mizoram)** by clicking 'Inspect →'."*

---

### Step 4: Interactive GIS Map & Open Data DEM Terrain (3:00 – 4:00)
> **Demonstrator**:  
> *(Scroll to the GIS Map section)*  
> *"Here on our interactive GIS map, markers indicate operational points overlaid on official Survey of India boundary polygons.*  
> *Notice our layer toggles: Risk Heatmap, Rainfall Intensity, and Road Corridors like **NH-306 (Silchar–Aizawl)** and **NH-2 (Dimapur–Imphal)**.*  
> *Terrain data was acquired through the **USGS / AWS Open Data Elevation Archive** (NASADEM 30m SRTM DEM) and processed to derive elevation, slope, aspect, and curvature features for all 131 districts. Terrain metrics provide environmental context while remaining computationally separate from our ML model."*

---

### Step 5: Promoted Machine Learning Model & Explainable AI (4:00 – 5:00)
> **Demonstrator**:  
> *(Scroll to Section 03: Explainable AI Engine)*  
> *"Our risk feed is powered by a promoted Random Forest classifier (`candidate_a_rf_v1` v1.1.0) evaluated on a temporally separated holdout dataset, achieving ~0.9206 ROC-AUC and ~0.9328 PR-AUC. Earlier 0.99+ estimates were identified as temporally contaminated and discarded.*  
> *The model operates on a strict **7-feature contract**: spatial coordinates, 1-day, 3-day, and 7-day rainfall accumulation, and seasonality.*  
> *Under 'Why This Result?', we display **Model-Level Feature Importance**: 24-hour rainfall contributes 23.3%, 3-day rain 22.9%, and 7-day rain 22.5%. We explicitly set local attribution to false to prevent fabricating unverified SHAP approximations."*

---

### Step 6: Decoupled Exposure & Data Quality Transparency (5:00 – 6:00)
> **Demonstrator**:  
> *(Point to the Exposure Card and Data Status indicators)*  
> *"Crucially, **ML Hazard Risk ($P \in [0, 1]$) and P7C Exposure/Vulnerability Scores ($S \in [0, 100]$) are 100% DECOUPLED** and NEVER multiplied into a single fake score.*  
> *Our exposure indicators draw from authoritative sources: UDISE+ schools, MoHFW healthcare facilities, MoRTH highway length, and NITI Aayog Multidimensional Poverty Index.*  
> *We maintain data integrity: for districts where open exposure data is incomplete, we state **INSUFFICIENT DATA** with score null, rather than substituting synthetic zeros.*  
> *Similarly, if live weather data is missing, the system gates risk to **DATA UNAVAILABLE**; if weather is stale, confidence is automatically downgraded."*

---

### Step 7: Human-in-the-Loop Protocol & Conclusion (6:00 – 7:00)
> **Demonstrator**:  
> *(Highlight the 4-Point Human Verification Checklist)*  
> *"Finally, NexSolve enforces a 4-point human verification checklist before any operational action:*  
> 1. Verify local station rainfall accumulation.  
> 2. Inspect crowd-sourced field observations.  
> 3. Check exposed road corridors and critical infrastructure.  
> 4. Confirm decisions with authorized SDMA/NDMA personnel.  
> 
> *In summary, NexSolve brings scientific rigor, spatial accuracy, data quality transparency, and human-in-the-loop governance to landslide risk decision support in Northeast India. Thank you, and we welcome your questions!"*

---

## Emergency Q&A Quick Reference

- **Q: Is this deployed live for government use?**  
  *A: "Containerized deployment configuration is prepared and tested via production-like readiness probes (`GET /api/ready`). Public cloud deployment requires evaluator cloud project credentials."*

- **Q: Why did you not include slope angle in the ML model?**  
  *A: "To prevent overfitting on static terrain features and maintain a leakage-free 7-feature model contract. Slope angle is presented alongside risk as environmental decision context."*

- **Q: Are the decision thresholds official government thresholds?**  
  *A: "No. The thresholds (0.35 Elevated, 0.50 Warning, 0.75 Emergency) are internal prototype markers derived from candidate threshold evaluation."*
