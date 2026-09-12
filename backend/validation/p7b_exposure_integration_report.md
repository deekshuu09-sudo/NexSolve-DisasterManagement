# P7B Exposure Data Acquisition & Integration Report

## Executive Summary
Phase 7B Exposure Data Acquisition and Integration has been successfully executed. High-priority authoritative Class A & B exposure and vulnerability datasets have been acquired, validated, normalized, and joined to official Survey of India (SoI) 131-district administrative boundaries across all 8 North Eastern Region (NER) states.

The production ML model (`candidate_a_rf_v1.pkl`), 7-feature model schema, model registry, and P6 risk decision engine (`risk_decision_engine.py`) remain **100% byte-for-byte unchanged and frozen**. Exposure metrics are exposed via a read-only API endpoint (`GET /api/exposure/{district_id}`) and displayed in the UI with explicit availability and reference-year badges.

---

## 1. Datasets Acquired & Provenance Summary

| Dataset ID | Dataset Name | Provider | Source Format / CRS | Reference Year | SHA-256 Checksum | District Coverage | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `exp_vuln_niti_mpi_2023` | NITI Aayog Multidimensional Poverty Index | NITI Aayog, GoI | JSON / EPSG:4326 | 2023 Progress Report | `66af96b1c31de66fefe7c2c3cbca411ae6930324e482cac69a15c07d02a3612f` | 131 / 131 | **ACQUIRED** |
| `exp_vuln_bmtpc_atlas_2023` | BMTPC Vulnerability Atlas of India | BMTPC, MoHUA, GoI | JSON / EPSG:4326 | 2019-2023 | `4c7ef9b8713c619230fad23c621ee100e133ba3eb1754f8c24563a024ce23f6f` | 131 / 131 | **ACQUIRED** |
| `exp_infra_mohfw_hfr` | Health Facility Registry (HFR) | MoHFW / NHA, GoI | JSON / EPSG:4326 | 2023-2024 | `742552ba5c40b30b2346c97b30bd0ccd69bbcebedae5b043f58ee161b52d4a8f` | 131 / 131 | **ACQUIRED** |
| `exp_infra_udise_plus` | UDISE+ School & Shelter Registry | Min. of Education, GoI | JSON / EPSG:4326 | 2022-2024 | `ab154d3021d3b04780e7e551a089e774cc3cf5024a6a09c267d8814f5798cc5f` | 131 / 131 | **ACQUIRED** |
| `exp_road_morth_nhai_gis` | MoRTH / NHAI National Highway GIS | MoRTH / NHAI, GoI | JSON / EPSG:4326 | 2023-2024 | `9947892e76eb75d25e71063d5adf63690c91591d876bdf7c93baffb3cde94109` | Arterial Corridors | **ACQUIRED** |
| `exp_pop_census_2011` | Census of India 2011 Primary Census | ORGI, MHA, GoI | JSON / EPSG:4326 | 2011 | `c4906f66c1a88b2a966384dcfe7a4a5468d615fe5713295cb2633be01a5ba375` | 131 / 131 | **ACQUIRED** |

---

## 2. Datasets Not Acquired (Reasoning & Limitations)

1. **`exp_built_isro_bhuvan_lulc` (ISRO Bhuvan LULC 1:50,000)**:
   - *Status*: **NOT ACQUIRED — SOURCE ACCESS LIMITATION**
   - *Reason*: ISRO Bhuvan WMS raster stream is active in frontend map tiles; direct vector GeoTIFF download requires NRSC geoportal user credential authorization. Documented as `PARTIAL` / `WMS_TILE_LAYER_ACTIVE`.
2. **`exp_pop_landscan_2022` (LandScan Global Population)**:
   - *Status*: **NOT ACQUIRED — PROPRIETARY LICENSE BLOCK**
   - *Reason*: Proprietary Oak Ridge National Laboratory (ORNL) license prohibits inclusion in open SIH prototype codebases. Rejected.

---

## 3. Spatial Reference & District Joining Governance
- **Authoritative Boundaries**: Official Survey of India (SoI) GeoJSON boundaries (`backend/data/geojson/ner_districts_soi.geojson` - 131 Districts, 8 NER States).
- **District Join Metadata**: Every district exposure record preserves official LGD district code (`dist_lgd`), SoI district name (`district_name_soi`), and state LGD code (`state_lgd`).
- **OpenStreetMap Policy**: OpenStreetMap vector geometry is classified as **Class C (Contextual Only)** and NEVER replaces official SoI boundaries or official MoRTH highway routes.

---

## 4. Missing Data & Zero-Filling Policy
- **No Synthetic Numbers**: Zero fake population values, hospital bed counts, or school numbers were generated.
- **Explicit Availability**: Missing or unacquired domain attributes remain `null` with domain status set to `UNAVAILABLE` or `PARTIAL`.
- **API Distinction**: API payloads distinguish between "zero facilities found" and "dataset unavailable".

---

## 5. API & Frontend Changes
- **Backend API**: Added `GET /api/exposure/{district_id}` endpoint in `backend/main.py` leveraging `backend/services/exposure_service.py`.
- **Frontend UI**: Extended `frontend/src/lib/api.ts` with `ExposureRecord` interface and `getExposure()` helper. Updated `frontend/src/App.tsx` with an Exposure & Vulnerability Intelligence card displaying Healthcare, Education, Transport, Demographic, and Vulnerability baselines with reference-year badges (`[Ref: 2024 MoHFW HFR]`, `[Ref: 2023 NITI Aayog MPI]`, etc.).

---

## 6. Verification & Automated Test Results
1. **Full Backend Test Suite**: `python3 -m unittest discover -s backend -p "test_*.py"`
   - Result: **Ran 95 tests in 16.585s — 95/95 PASSED (100% OK)**.
2. **Frontend Production Build**: `npm run build` in `frontend/`
   - Result: **PASS** (`tsc -b && vite build` succeeded cleanly with zero errors).
3. **Model Artifact Integrity**:
   - Original production model `landslide_model.pkl` SHA-256: `d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1` (**UNTOUCHED**).
   - Promoted Candidate A `candidate_a_rf_v1.pkl` SHA-256: `1acad34e85b53df0cb68e5e81cd81d68066c4173792e65a51288b35557ba0f72` (**UNTOUCHED**).
4. **P6 Decision Engine & Thresholds**:
   - `risk_decision_engine.py` and `risk_policy.json` (v1.0.0-PROTOTYPE) are 100% unchanged.

---

## 7. Remaining Gaps & P7C Roadmap
- **Demographic Projections**: 2011 Census population baselines require official ORGI state growth factors for 2026 demographic projections.
- **Sub-District Vulnerability**: Higher-resolution block/gram-panchayat exposure disaggregation when finer telemetry becomes available in future phases.
- **P7C Note**: P7B is complete. Vulnerability scoring and ML feature integration are deferred to future governed phases.
