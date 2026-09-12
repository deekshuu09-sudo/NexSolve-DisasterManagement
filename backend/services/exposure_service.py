"""NexSolve Read-Only Exposure & Vulnerability Intelligence Service.

Serves validated exposure layers (demographic, vulnerability, healthcare, education, transport, built environment)
joined to official Survey of India (SoI) district boundaries.
P0 Safety Control: Returns explicit UNAVAILABLE / null states for unacquired datasets without synthetic zero-filling.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

PROCESSED_EXPOSURE_PATH = Path(__file__).resolve().parents[1] / "data" / "exposure" / "processed" / "district_exposure_summary.json"


def load_exposure_database() -> dict[str, Any]:
    """Load normalized district exposure summary dataset."""
    if PROCESSED_EXPOSURE_PATH.exists():
        try:
            with open(PROCESSED_EXPOSURE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"schema_version": "1.0.0", "total_districts": 0, "districts": {}}


EXPOSURE_DB = load_exposure_database()


OP_SOI_MATCHES = {
    "cherrapunji": "east_khasi_hills",
    "sohra": "east_khasi_hills",
}


def get_district_exposure(district_id: str) -> dict[str, Any]:
    """Retrieve verified exposure & vulnerability record for a district.

    Returns district exposure data alongside domain availability flags and provenance metadata.
    """
    global EXPOSURE_DB
    if not EXPOSURE_DB.get("districts"):
        EXPOSURE_DB = load_exposure_database()

    districts = EXPOSURE_DB.get("districts", {})
    did_clean = district_id.lower().strip()
    did_clean = OP_SOI_MATCHES.get(did_clean, did_clean)

    # Search by exact district_id or district_name match
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
            "demographic": record.get("demographic"),
            "vulnerability": record.get("vulnerability"),
            "healthcare": record.get("healthcare"),
            "education": record.get("education"),
            "transport": record.get("transport"),
            "built_environment": record.get("built_environment"),
            "availability": record.get("availability", {}),
            "provenance": record.get("provenance", []),
        }

    # Return explicit UNAVAILABLE status if district has no acquired exposure record
    return {
        "success": True,
        "district_id": district_id,
        "district_name_soi": district_id.replace("_", " ").title(),
        "state_name": "NER Region",
        "dist_lgd": None,
        "status": "UNAVAILABLE",
        "demographic": None,
        "vulnerability": None,
        "healthcare": None,
        "education": None,
        "transport": None,
        "built_environment": {
            "reference_year": "2021",
            "source": "ISRO Bhuvan LULC WMS Stream (Vector extract NOT ACQUIRED — SOURCE ACCESS LIMITATION)",
            "built_up_area_sqkm": None,
            "status": "WMS_TILE_LAYER_ACTIVE",
        },
        "availability": {
            "demographic": "UNAVAILABLE",
            "vulnerability": "UNAVAILABLE",
            "healthcare": "UNAVAILABLE",
            "education": "UNAVAILABLE",
            "transport": "UNAVAILABLE",
            "built_environment": "PARTIAL",
        },
        "provenance": [],
        "message": "Exposure data unavailable for this district. No synthetic values generated.",
    }
