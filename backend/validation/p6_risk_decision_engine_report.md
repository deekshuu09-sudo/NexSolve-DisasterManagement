# P6 Risk & Alert Decision Engine

## Current Architecture
The NexSolve Risk & Alert Decision Engine (`backend/services/risk_decision_engine.py`) sits directly on top of model prediction outputs (`backend/model/predictor.py`), weather feed services (`backend/data/weather_service.py`), and regional geospatial layers. It converts ML predictions and environmental observations into structured, decision-support alert objects.

```
Live Weather Feed / Sensor Data ────────┐
                                        ├──► ML Predictor (candidate_a_rf_v1) ──► Risk Decision Engine ──► API Response & UI
Central Policy (risk_policy.json) ──────┘                                        (evaluate_risk_decision)
```

## Decision Logic
The decision engine evaluates incoming model outputs and weather metadata against configurable thresholds stored in `backend/data/config/risk_policy.json`. Every decision produces a structured `RiskDecision` object containing:
- **Decision Status**: `EVALUATED` or `NOT_EVALUABLE`
- **Internal Risk Level**: `GREEN`, `YELLOW`, `ORANGE`, `RED`, or `DATA_UNAVAILABLE`
- **Probability & Confidence**: `risk_probability` (0.0 to 1.0) and categorical `confidence` (`HIGH`, `MEDIUM`, `LOW`, `UNAVAILABLE`)
- **Machine-Readable Reason Codes**: `WEATHER_FEED_LIVE`, `RAIN_1D_ELEVATED`, `MODEL_HIGH_RISK`, etc.
- **Authority Recommendation**: Actionable advice for disaster-management personnel.

## Risk Levels
NexSolve uses four **INTERNAL DECISION-SUPPORT** levels:
- **GREEN** (`Normal Risk`): Lower estimated risk based on current weather observations (`probability < 0.35`).
- **YELLOW** (`Watch`): Increased attention recommended (`0.35 <= probability < 0.50`).
- **ORANGE** (`Warning`): Preparedness and resource positioning recommended (`0.50 <= probability < 0.75`).
- **RED** (`Emergency Support`): Immediate authority assessment recommended (`probability >= 0.75`).
- **DATA_UNAVAILABLE**: Live weather feed is offline or required inputs are missing.

*Note: These levels are NexSolve internal decision-support markers and do NOT replace official NDMA/SDMA emergency alert categories.*

## Threshold Policy
Thresholds are centrally managed in `backend/data/config/risk_policy.json`:
- `candidate_internal_threshold`: `0.35`
- `default_comparison_threshold`: `0.50`
- `elevated_risk_threshold`: `0.35`
- `warning_risk_threshold`: `0.50`
- `emergency_risk_threshold`: `0.75`
- `rainfall_24h_elevated_mm`: `50.0`
- `rainfall_3d_elevated_mm`: `100.0`
- `rainfall_7d_elevated_mm`: `200.0`

Policy Version: `1.0.0-PROTOTYPE` (Status: `PROTOTYPE / INTERNAL`).

## Data Availability Rules
**P0 Safety Control**: If live weather data is offline or required rainfall fields (`rainfall_1d`, `rainfall_3d`, `rainfall_7d`) are missing/null:
- `risk_probability` is set to `null` (NOT `0%` or `0.0`).
- `risk_level` is set to `"DATA_UNAVAILABLE"`.
- `confidence` is set to `"UNAVAILABLE"`.
- `decision_status` is set to `"NOT_EVALUABLE"`.
- Historical archive datasets are NEVER silently substituted for live weather feeds in risk evaluation.

## Confidence Handling
Model probability score is kept strictly distinct from decision confidence:
- **HIGH**: Verified live weather feed, observation age <= 3.0 hours, complete feature set.
- **MEDIUM**: Stale weather feed (observation age > 3.0 hours) or data lag.
- **LOW**: Degraded or border observation conditions.
- **UNAVAILABLE**: Live weather feed offline or input features missing.

## Reason Codes
The decision engine emits machine-readable reason codes strictly supported by empirical inputs:
- `RAIN_1D_ELEVATED` (24h rainfall >= 50.0 mm)
- `RAIN_3D_ELEVATED` (3-day rainfall >= 100.0 mm)
- `RAIN_7D_ELEVATED` (7-day rainfall >= 200.0 mm)
- `SEASONAL_FACTOR` (Monsoon period May–Sept)
- `MODEL_HIGH_RISK` (Probability >= 0.75)
- `MODEL_ELEVATED_RISK` (0.35 <= Probability < 0.75)
- `MODEL_LOW_RISK` (Probability < 0.35)
- `WEATHER_FEED_LIVE` / `WEATHER_FEED_STALE` / `WEATHER_FEED_UNAVAILABLE`

## Recommended Actions
Conservative, authority-facing recommendations:
- **GREEN**: *"Continue routine monitoring."*
- **YELLOW**: *"Increase monitoring and review local conditions."*
- **ORANGE**: *"Prepare response resources and verify field conditions."*
- **RED**: *"Escalate to authorized disaster-management personnel for immediate assessment."*
- **DATA_UNAVAILABLE**: *"Verify local weather station feed and field sensors."*

## API Changes
- Extended `POST /api/risk`, `/api/districts`, `/api/districts/{district_id}`, and `/api/forecast/{district_id}` response payloads with a structured `decision` object while preserving 100% backward compatibility for existing fields (`riskScore`, `status`, `confidence`, `factors`, `modelSource`).

## Frontend Changes
- Updated `frontend/src/lib/api.ts` with `RiskDecision` interface.
- Updated `frontend/src/App.tsx`:
  - Added explicit **"NexSolve Decision Support"** badges and disclaimers across XAI, Threat Intel, and Response Matrix panels.
  - Visual display of `DATA UNAVAILABLE` when weather feeds are offline (preventing misleading `0%` or `LOW RISK` badges).
  - Footer display of active policy (`risk_policy.json` v1.0.0-PROTOTYPE) and promoted candidate model (`candidate_a_rf_v1` v1.1.0).

## Safety Controls
1. **No Public Evacuation Orders**: Automated messages do NOT issue public evacuation commands.
2. **No False Government Claims**: UI and API disclaimers state that NexSolve outputs are decision-support tools and do NOT claim NDMA/SDMA official authority.
3. **No Retraining or Feature Changes**: ML model weights, 7-feature schema, and model pickle artifacts were completely untouched during P6.

## Tests
- Automated test suite `backend/test_risk_decision_engine.py` covers 17 distinct operational scenarios.
- Full test run passed **85 / 85 unit tests**.
- Frontend production build (`npm run build`) passed with **0 errors**.

## Limitations
- Prototype policy thresholds (`0.35`, `0.50`, `0.75`) require further long-term field calibration.
- Multi-hazard cascades (e.g. earthquake-induced landslides or glacial lake outbursts) are not yet integrated into the decision rules.

## Future Work
- Integration with persistent decision audit logging database.
- Multi-criteria decision support incorporating real-time DEM slope angle and soil saturation telemetry when live sensor streams become available.
