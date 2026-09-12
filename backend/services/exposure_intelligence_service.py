"""NexSolve Exposure & Vulnerability Intelligence Service.

Serves min-max normalized district exposure indicators, data completeness metrics,
composite prototype vulnerability scores (0-100), and contributing factor breakdowns.

Reads:
- `backend/data/exposure/processed/district_vulnerability_profiles.json`

Safety Controls:
- 100% strict separation from ML landslide risk model (`candidate_a_rf_v1.pkl`).
- Missing values remain `null` / `UNAVAILABLE` without zero-filling.
- Includes non-official prototype disclaimer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROCESSED_PROFILES_PATH = Path(__file__).resolve().parents[1] / "data" / "exposure" / "processed" / "district_vulnerability_profiles.json"


def load_vulnerability_database() -> dict[str, Any]:
    """Load calculated district vulnerability profiles."""
    if PROCESSED_PROFILES_PATH.exists():
        try:
            with open(PROCESSED_PROFILES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "schema_version": "1.0.0-PROTOTYPE",
        "policy_version": "1.0.0-PROTOTYPE",
        "total_districts": 0,
        "districts": {},
        "disclaimer": "NexSolve Prototype Exposure/Vulnerability Scoring Framework — Information for decision-support assessment only. Not an official government emergency alert category or prediction model.",
    }


VULNERABILITY_DB = load_vulnerability_database()


OP_SOI_MATCHES = {
    "cherrapunji": "east_khasi_hills",
    "sohra": "east_khasi_hills",
}


def get_vulnerability_profile(district_id: str) -> dict[str, Any]:
    """Retrieve district vulnerability profile including normalized indicators, completeness %,

    composite score (0-100), and contributing factor decomposition.
    """
    global VULNERABILITY_DB
    if not VULNERABILITY_DB.get("districts"):
        VULNERABILITY_DB = load_vulnerability_database()

    districts = VULNERABILITY_DB.get("districts", {})
    did_clean = district_id.lower().strip()
    did_clean = OP_SOI_MATCHES.get(did_clean, did_clean)

    record = districts.get(did_clean)
    if not record:
        for k, v in districts.items():
            if k == did_clean or v.get("district_name_soi", "").lower() == did_clean:
                record = v
                break

    if record:
        return {
            "success": True,
            "district_id": record["district_id"],
            "district_name_soi": record["district_name_soi"],
            "state_name": record["state_name"],
            "dist_lgd": record.get("dist_lgd"),
            "status": record["status"],
            "confidence": record["confidence"],
            "data_completeness_pct": record["data_completeness_pct"],
            "available_domains_count": record["available_domains_count"],
            "total_domains_count": record["total_domains_count"],
            "composite_vulnerability_score": record["composite_vulnerability_score"],
            "domains": record.get("domains", {}),
            "contributing_factors": record.get("contributing_factors", []),
            "provenance": record.get("provenance", []),
            "disclaimer": record.get("disclaimer") or VULNERABILITY_DB.get("disclaimer"),
        }

    # Return explicit INSUFFICIENT_DATA / UNAVAILABLE response if district has no profile
    return {
        "success": True,
        "district_id": district_id,
        "district_name_soi": district_id.replace("_", " ").title(),
        "state_name": "NER Region",
        "dist_lgd": None,
        "status": "INSUFFICIENT_DATA",
        "confidence": "UNAVAILABLE",
        "data_completeness_pct": 0.0,
        "available_domains_count": 0,
        "total_domains_count": 5,
        "composite_vulnerability_score": None,
        "domains": {},
        "contributing_factors": [],
        "provenance": [],
        "disclaimer": VULNERABILITY_DB.get("disclaimer"),
        "message": "Vulnerability profile unavailable for this district. No synthetic values generated.",
    }
