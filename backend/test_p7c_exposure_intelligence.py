"""Unit tests for NexSolve P7C Exposure Intelligence & Vulnerability Assessment.

Verifies:
1. Vulnerability profile generation & schema compliance
2. GET /api/vulnerability/{district_id} endpoint response schema
3. GET /api/exposure/{district_id} nested vulnerability intelligence object
4. Case-insensitive district lookup logic
5. Indicator Min-Max normalization score bounds (0.0 to 1.0)
6. Missing data semantics (null / UNAVAILABLE without zero-filling)
7. District data completeness percentage calculation
8. Renormalized composite vulnerability score (0-100) across available domain weights
9. Contributing factor decomposition sum matching ~100%
10. Explicit prototype non-official disclaimer present in profiles
11. Preserved production model SHA256 (landslide_model.pkl: d8546b0f7837...)
12. Preserved promoted Candidate A SHA256 (candidate_a_rf_v1.pkl: 1acad34e85...)
13. Preserved P6 Risk Decision Engine policy & threshold behavior
14. Health bed capacity lower-is-higher vulnerability directionality
15. SoI 131-district complete spatial coverage accounting
"""

import hashlib
import json
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.exposure_intelligence_service import get_vulnerability_profile, load_vulnerability_database
from backend.services.risk_decision_engine import evaluate_risk_decision

ROOT = Path(__file__).resolve().parents[1]
LANDSLIDE_MODEL_PATH = ROOT / "backend" / "model" / "landslide_model.pkl"
CANDIDATE_A_PATH = ROOT / "backend" / "model" / "experimental" / "candidate_a_rf_v1.pkl"
PROFILES_PATH = ROOT / "backend" / "data" / "exposure" / "processed" / "district_vulnerability_profiles.json"
POLICY_PATH = ROOT / "backend" / "data" / "config" / "exposure_policy.json"


class TestP7CExposureIntelligence(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_vulnerability_profiles_file_exists(self):
        """Verify district_vulnerability_profiles.json exists and is valid JSON."""
        self.assertTrue(PROFILES_PATH.exists(), f"Profiles file missing at {PROFILES_PATH}")
        with open(PROFILES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("schema_version"), "1.0.0-PROTOTYPE")
        self.assertEqual(data.get("total_districts"), 131)
        self.assertIn("disclaimer", data)

    def test_02_exposure_policy_configuration(self):
        """Verify exposure_policy.json defines 5 core domains and valid weights summing to 1.0."""
        self.assertTrue(POLICY_PATH.exists(), f"Policy file missing at {POLICY_PATH}")
        with open(POLICY_PATH, "r", encoding="utf-8") as f:
            policy = json.load(f)
        domains = policy.get("domains", {})
        self.assertEqual(len(domains), 5)
        total_weight = sum(d["weight"] for d in domains.values())
        self.assertAlmostEqual(total_weight, 1.0, places=4)

    def test_03_get_vulnerability_profile_valid_district(self):
        """Verify get_vulnerability_profile returns COMPUTED/HIGH for Champhai with 100% completeness."""
        res = get_vulnerability_profile("champhai")
        self.assertTrue(res["success"])
        self.assertEqual(res["district_id"], "champhai")
        self.assertEqual(res["status"], "COMPUTED")
        self.assertEqual(res["confidence"], "HIGH")
        self.assertEqual(res["data_completeness_pct"], 100.0)
        self.assertIsNotNone(res["composite_vulnerability_score"])
        self.assertTrue(0.0 <= res["composite_vulnerability_score"] <= 100.0)
        self.assertEqual(len(res["domains"]), 5)
        self.assertTrue(len(res["contributing_factors"]) > 0)

    def test_04_get_vulnerability_profile_unknown_district(self):
        """Verify unknown district returns INSUFFICIENT_DATA / UNAVAILABLE with null composite score."""
        res = get_vulnerability_profile("unknown_district_xyz")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "INSUFFICIENT_DATA")
        self.assertEqual(res["confidence"], "UNAVAILABLE")
        self.assertEqual(res["data_completeness_pct"], 0.0)
        self.assertIsNone(res["composite_vulnerability_score"])
        self.assertEqual(res["available_domains_count"], 0)

    def test_05_case_insensitive_district_lookup(self):
        """Verify district lookup works for Champhai, CHAMPHAI, or champhai."""
        res1 = get_vulnerability_profile("champhai")
        res2 = get_vulnerability_profile("CHAMPHAI")
        res3 = get_vulnerability_profile("Champhai")
        self.assertEqual(res1["district_id"], res2["district_id"])
        self.assertEqual(res2["district_id"], res3["district_id"])
        self.assertEqual(res1["composite_vulnerability_score"], res2["composite_vulnerability_score"])

    def test_06_indicator_min_max_bounds(self):
        """Verify all computed normalized scores across all districts lie within [0.0, 1.0]."""
        db = load_vulnerability_database()
        districts = db.get("districts", {})
        for d_id, d_data in districts.items():
            for d_key, domain in d_data.get("domains", {}).items():
                norm = domain.get("normalized_score")
                if norm is not None:
                    self.assertTrue(0.0 <= norm <= 1.0, f"Normalized score {norm} out of bounds for {d_id}.{d_key}")

    def test_07_missing_data_semantics_no_zero_fill(self):
        """Verify unacquired domain indicators are set to null/UNAVAILABLE rather than zero-filled."""
        res = get_vulnerability_profile("anjaw")
        self.assertEqual(res["status"], "INSUFFICIENT_DATA")
        self.assertEqual(res["available_domains_count"], 0)
        for d_key, domain in res["domains"].items():
            self.assertEqual(domain["status"], "UNAVAILABLE")
            self.assertIsNone(domain["raw_value"])
            self.assertIsNone(domain["normalized_score"])

    def test_08_data_completeness_percentage_calculation(self):
        """Verify data completeness % equals (available_domains_count / 5) * 100."""
        db = load_vulnerability_database()
        for d_id, d_data in db.get("districts", {}).items():
            avail = d_data.get("available_domains_count", 0)
            total = d_data.get("total_domains_count", 5)
            expected_pct = round((avail / total) * 100.0, 1)
            self.assertEqual(d_data.get("data_completeness_pct"), expected_pct)

    def test_09_contributing_factors_sum_to_100(self):
        """Verify sum of contributing factor percentages equals ~100% for computed profiles."""
        res = get_vulnerability_profile("champhai")
        factors = res.get("contributing_factors", [])
        self.assertTrue(len(factors) > 0)
        total_contrib = sum(f["contribution_pct"] for f in factors)
        self.assertAlmostEqual(total_contrib, 100.0, delta=0.5)

    def test_10_disclaimer_presence(self):
        """Verify non-official prototype disclaimer is present in vulnerability profile outputs."""
        res = get_vulnerability_profile("champhai")
        self.assertIn("disclaimer", res)
        self.assertIn("NexSolve Prototype Exposure/Vulnerability", res["disclaimer"])

    def test_11_api_vulnerability_endpoint(self):
        """Verify GET /api/vulnerability/{district_id} returns 200 OK with vulnerability profile."""
        res = self.client.get("/api/vulnerability/champhai")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["district_id"], "champhai")
        self.assertEqual(data["status"], "COMPUTED")
        self.assertIn("composite_vulnerability_score", data)
        self.assertIn("contributing_factors", data)

    def test_12_api_exposure_endpoint_nested_intelligence(self):
        """Verify GET /api/exposure/{district_id} includes nested vulnerability_intelligence object."""
        res = self.client.get("/api/exposure/champhai")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("vulnerability_intelligence", data)
        vuln = data["vulnerability_intelligence"]
        self.assertEqual(vuln["district_id"], "champhai")
        self.assertEqual(vuln["status"], "COMPUTED")

    def test_13_healthcare_directionality_handling(self):
        """Verify healthcare lower bed capacity results in higher normalized vulnerability score."""
        db = load_vulnerability_database()
        bounds = db.get("normalization_bounds", {}).get("healthcare", {})
        min_beds = bounds.get("min")
        max_beds = bounds.get("max")
        if min_beds is not None and max_beds is not None and max_beds > min_beds:
            # Check a district with lower beds vs higher beds
            for d_id, d_data in db.get("districts", {}).items():
                hc = d_data.get("domains", {}).get("healthcare", {})
                if hc.get("status") == "AVAILABLE":
                    raw = hc.get("raw_value")
                    norm = hc.get("normalized_score")
                    expected_norm = round((max_beds - raw) / (max_beds - min_beds), 4)
                    self.assertAlmostEqual(norm, expected_norm, places=3)

    def test_14_production_model_sha256_preservation(self):
        """Verify original production model landslide_model.pkl SHA256 remains d8546b0f78372c..."""
        with open(LANDSLIDE_MODEL_PATH, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1")

    def test_15_candidate_a_model_sha256_preservation(self):
        """Verify candidate_a_rf_v1.pkl artifact SHA256 remains 1acad34e85b53df0cb..."""
        with open(CANDIDATE_A_PATH, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, "1acad34e85b53df0cb68e5e81cd81d68066c4173792e65a51288b35557ba0f72")

    def test_16_p6_risk_decision_engine_unchanged(self):
        """Verify P6 risk decision engine functionality and policy thresholds remain frozen and intact."""
        decision = evaluate_risk_decision(
            model_prediction={"riskScore": 85, "status": "COMPUTED"},
            weather_data={"available": True, "rainfall_1d": 146.0, "is_live": True, "quality": "good"},
            location={"lat": 23.4756, "lng": 93.3289, "state": "Mizoram", "district": "Champhai"},
        )
        dec_dict = decision.to_dict()
        self.assertEqual(dec_dict["riskLevel"], "RED")
        self.assertEqual(dec_dict["decisionStatus"], "EVALUATED")
        self.assertFalse(dec_dict["isOfficialWarning"])

    def test_17_soi_131_districts_complete_accounting(self):
        """Verify all 131 official SoI districts are present in district_vulnerability_profiles.json."""
        db = load_vulnerability_database()
        districts = db.get("districts", {})
        self.assertEqual(len(districts), 131)


if __name__ == "__main__":
    unittest.main()
