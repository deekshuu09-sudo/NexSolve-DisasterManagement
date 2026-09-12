# NexSolve Exposure & Vulnerability Intelligence (P7A Data Discovery)

## Overview
This directory contains the authoritative data inventory, classification framework, and provenance audit for **Phase 7A: Exposure & Vulnerability Intelligence Data Discovery**.

The objective of P7A is to identify, document, and classify authoritative datasets covering population exposure, built-up settlements, transport corridors, critical infrastructure, emergency facilities, and socio-economic vulnerability across the 8 North Eastern Region (NER) states of India.

---

## Governance & Safety Rules
1. **P6 Pipeline & Model Frozen**: No modifications have been made to `backend/model/`, model artifacts (`candidate_a_rf_v1.pkl`), 7-feature model schema, training code, or the central risk decision engine (`risk_decision_engine.py`).
2. **Official Geographic Reference Preserved**: All spatial evaluations use the official Survey of India (SoI) administrative boundaries (`ner_states_soi.geojson` and `ner_districts_soi.geojson` - 8 States, 131 Districts).
3. **Zero Synthetic Data Pledge**: No fake population numbers, hospital bed counts, or road alignments have been generated or zero-filled.
4. **Authoritative Source Priority**: Government of India (Tier 1) and State Government (Tier 2) datasets take precedence over international research (Tier 3/4) and community mapping (Tier 5).
5. **OpenStreetMap Policy**: OpenStreetMap is classified as **Class C (Contextual Only)** and MUST NOT replace official Survey of India administrative boundaries or official government route definitions.

---

## Directory Contents

```
backend/data/exposure/
├── README.md               # Overview and governance guidelines
├── dataset_inventory.json  # Machine-readable JSON inventory of candidate datasets
└── provenance_notes.md     # Detailed provenance, classification, and licensing audit
```

---

## Candidate Dataset Summary

| Classification | Domain | Dataset Name | Provider | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Class A** | Built-up | ISRO Bhuvan LULC (1:50,000) | NRSC / ISRO (GoI) | Production-Grade |
| **Class A** | Transport | MoRTH / NHAI National Highway Network | MoRTH (GoI) | Production-Grade |
| **Class A** | Healthcare | Health Facility Registry (HFR) | MoHFW / NHA (GoI) | Production-Grade |
| **Class A** | Education | UDISE+ School Registry | Min. of Education (GoI) | Production-Grade |
| **Class A** | Vulnerability | NITI Aayog Multidimensional Poverty Index | NITI Aayog (GoI) | Production-Grade |
| **Class A** | Housing | BMTPC Vulnerability Atlas of India | MoHUA / BMTPC (GoI) | Production-Grade |
| **Class B** | Population | Census of India 2011 PCA | ORGI (GoI) | Usable (2011 Age Caveat) |
| **Class B** | Population | WorldPop Gridded Population (100m) | WorldPop / CIESIN | Usable (Disaggregated Grid) |
| **Class B** | Built-up | GHSL Built-up Surface (10m/100m) | EC JRC | Usable (Satellite Density) |
| **Class B** | Transport | PMGSY Rural Road Asset Database | MoRD (GoI) | Usable (Attribute Check) |
| **Class C** | Contextual | OpenStreetMap Road Network | OpenStreetMap | Contextual Display Only |
| **Class D** | Population | LandScan Global Population (1km) | ORNL / US DoE | REJECT (License Block) |

---

## Next Steps (Phase 7B)
Phase 7A establishes the dataset inventory and provenance audit. In Phase 7B (Vulnerability Scoring & Feature Extraction), selected Class A & B datasets will be ingested to form district-level exposure and vulnerability vectors without altering the underlying ML prediction contract.
