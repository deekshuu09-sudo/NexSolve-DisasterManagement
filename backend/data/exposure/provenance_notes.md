# P7A Exposure & Vulnerability Dataset Provenance & Governance Notes

## 1. Source Hierarchy & Priority Policy
All exposure and vulnerability data evaluated for the NexSolve platform must strictly adhere to the following 5-tier source hierarchy:

1. **Tier 1 — Government of India / Official Government Sources** (e.g. Census of India, NRSC/ISRO Bhuvan, MoRTH/NHAI, MoHFW HFR, UDISE+, NITI Aayog, BMTPC).
2. **Tier 2 — State Government Sources** (e.g. State PWD, State SDMA geospatial portals).
3. **Tier 3 — International Public Datasets with Verified Provenance** (e.g. European Commission GHSL, WorldPop UN-aligned grids).
4. **Tier 4 — Reputable Research Datasets** (Peer-reviewed, published methodology datasets).
5. **Tier 5 — Open Community Datasets** (e.g. OpenStreetMap — Class C Contextual ONLY).

> **STRICT RULE**: Random GitHub repositories, Kaggle uploads, web-scraped spreadsheets, or fabricated CSVs are **STRICTLY REJECTED** as authoritative sources.

---

## 2. Spatial Reference & Boundary Governance
- **Spatial Reference System**: Official Survey of India (SoI) Administrative Boundaries (`backend/data/geojson/ner_states_soi.geojson` and `backend/data/geojson/ner_districts_soi.geojson`).
- **State Scope**: 8 North Eastern Region (NER) States:
  1. Arunachal Pradesh
  2. Assam
  3. Manipur
  4. Meghalaya
  5. Mizoram
  6. Nagaland
  7. Sikkim
  8. Tripura
- **District Scope**: Exactly 131 Districts defined in the Survey of India LGD boundary database.
- **Rule on OpenStreetMap (OSM)**: OSM vector geometry (roads, buildings, facilities) MAY be used for supplementary contextual rendering, but **MUST NEVER** overwrite, alter, or replace official Survey of India administrative boundaries or official government highway route definitions.

---

## 3. Dataset Classification Summary

| Dataset ID | Dataset Name | Domain | Classification | Authoritative Tier | SIH Redistribution | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `exp_built_isro_bhuvan_lulc` | ISRO Bhuvan LULC 1:50k & Built-up | Built-up | **Class A** | Official GoI (ISRO) | YES | SAFE |
| `exp_road_morth_nhai_gis` | MoRTH / NHAI National Highway Network | Highways | **Class A** | Official GoI (MoRTH) | YES | SAFE |
| `exp_infra_mohfw_hfr` | MoHFW Health Facility Registry (HFR) | Healthcare | **Class A** | Official GoI (MoHFW) | YES | SAFE |
| `exp_infra_udise_plus` | UDISE+ School & Shelter Registry | Education | **Class A** | Official GoI (Min. of Edu) | YES | SAFE |
| `exp_vuln_niti_mpi_2023` | NITI Aayog Multidimensional Poverty Index | Vulnerability | **Class A** | Official GoI (NITI Aayog) | YES | SAFE |
| `exp_vuln_bmtpc_atlas_2023` | BMTPC Vulnerability Atlas of India | Housing / Risk | **Class A** | Official GoI (BMTPC) | YES | SAFE |
| `exp_pop_census_2011` | Census of India 2011 Primary Census Abstract | Population | **Class B** | Official GoI (ORGI) | YES | SAFE (with age caveat) |
| `exp_pop_worldpop_2020` | WorldPop Gridded Population (100m) | Population | **Class B** | International Research | YES | SAFE (spatial overlay) |
| `exp_built_ghsl_jrc_2020` | GHSL Built-up Surface (GHS-BUILT-S) | Built-up | **Class B** | International Research | YES | SAFE (density check) |
| `exp_road_pmgsy_ommas` | PMGSY Rural Road Asset Database | Rural Roads | **Class B** | Official GoI (MoRD) | YES | SAFE (attribute check) |
| `exp_road_osm_overpass` | OpenStreetMap Road Network Overlay | Transport | **Class C** | Open Community | YES (ODbL) | CONTEXTUAL ONLY |
| `exp_pop_landscan_2022` | LandScan Global Ambient Population | Population | **Class D** | Research (Restricted) | **NO** | **REJECTED (License)** |

---

## 4. Technical Integration & Access Requirements

### Credential & Access Requirements:
- **No Credentials Required**: Census 2011 PCA, WorldPop 100m, GHSL Built-up, MoRTH Highway GIS, NITI Aayog MPI, BMTPC Atlas, UDISE+ open portal, ABDM HFR public API.
- **Manual Download / Geoportal Request**: ISRO Bhuvan LULC (requires NRSC user registration for raw GeoTIFF/shapefile vectors; WMS stream is public), GeoPMGSY WMS.
- **Rejected due to License**: LandScan 2022 (requires ORNL proprietary license).

### Known Coverage Gaps & Limitations:
- **Temporal Gap**: Census of India 2011 is 15 years old. Decennial census 2021 was delayed. District-level population totals require compounding growth rate adjustments (e.g. 2011-2026 state-level projection factors published by ORGI Technical Group on Population Projections).
- **Spatial Resolution & Remote Terrain**: Remote border districts in Arunachal Pradesh (e.g., Anjaw, Dibang Valley) and Nagaland (Kiphire, Longleng) have lower density GPS telemetry in rural road databases (PMGSY).
- **Contextual OSM Layer**: OpenStreetMap coverage is high in capitals (Guwahati, Gangtok, Shillong, Aizawl) but sparse in upper hill blocks. Must be clearly marked as community-derived.

---

## 5. Anti-Fabrication & Zero Synthetic Data Pledge
- **No Synthetic Numbers**: No fake population totals, hospital bed counts, or road lengths have been or will be generated.
- **No Zero-Filling**: Missing values will be represented as `null` or explicit `"DATA_UNAVAILABLE"` metadata, preserving P6 data gating principles.
- **Pipeline Preservation**: P6 decision logic (`risk_decision_engine.py`), model artifacts (`candidate_a_rf_v1.pkl`), and 7-feature model schema are completely frozen and untouched.
