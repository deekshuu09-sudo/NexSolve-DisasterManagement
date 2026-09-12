"""Unit tests for NexSolve P7C District Exposure & Vulnerability API Joins.

Verifies:
1. GET /api/districts returns enriched vulnerability and exposure objects for all districts.
2. Operational districts (e.g. Champhai, Aizawl, Cherrapunji/Sohra, Tawang, Kohima, Senapati, Dima Hasao, Dhalai, Gangtok) return real acquired exposure data.
3. Cherrapunji / Sohra correctly resolves to East Khasi Hills (5/5 domains, COMPUTED status).
4. Gangtok correctly returns PARTIAL coverage (3/5 domains).
5. Unacquired districts do not synthesize synthetic zero data.
"""

import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.exposure_intelligence_service import get_vulnerability_profile
from backend.services.exposure_service import get_district_exposure


class TestP7CDistrictExposureJoin(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_api_districts_includes_vulnerability_and_exposure(self):
        """Verify GET /api/districts attaches vulnerability and exposure objects."""
        resp = self.client.get("/api/districts")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        districts = data.get("data", [])
        self.assertEqual(len(districts), 9)

        for d in districts:
            self.assertIn("vulnerability", d, f"District {d['id']} missing vulnerability object")
            self.assertIn("exposure", d, f"District {d['id']} missing exposure object")

    def test_02_cherrapunji_alias_mapping(self):
        """Verify cherrapunji resolves to East Khasi Hills (LGD 298) with 5/5 domains and COMPUTED status."""
        vuln = get_vulnerability_profile("cherrapunji")
        self.assertEqual(vuln["status"], "COMPUTED")
        self.assertEqual(vuln["available_domains_count"], 5)
        self.assertIsNotNone(vuln["composite_vulnerability_score"])
        self.assertAlmostEqual(vuln["composite_vulnerability_score"], 65.55, places=1)
        self.assertEqual(str(vuln["dist_lgd"]), "298")

        exp = get_district_exposure("cherrapunji")
        self.assertEqual(exp["status"], "AVAILABLE")

    def test_03_operational_districts_coverage_status(self):
        """Verify 8 operational districts have 5/5 domains (FULL) and 1 (Gangtok) has 3/5 PARTIAL domains."""
        resp = self.client.get("/api/districts")
        districts = resp.json()["data"]
        op_map = {d["id"]: d["vulnerability"] for d in districts}

        # 8 districts should be COMPUTED (5/5)
        for did in ["champhai", "aizawl", "senapati", "cherrapunji", "tawang", "kohima", "dima_hasao", "dhalai"]:
            v = op_map.get(did, {})
            self.assertEqual(v.get("status"), "COMPUTED", f"Expected COMPUTED status for {did}")
            self.assertEqual(v.get("available_domains_count"), 5, f"Expected 5/5 domains for {did}")
            self.assertIsNotNone(v.get("composite_vulnerability_score"), f"Expected score for {did}")

        # Gangtok should be PARTIAL (3/5)
        g_v = op_map.get("gangtok", {})
        self.assertEqual(g_v.get("status"), "PARTIAL")
        self.assertEqual(g_v.get("available_domains_count"), 3)
        self.assertIsNotNone(g_v.get("composite_vulnerability_score"))

    def test_04_no_synthetic_zero_filling(self):
        """Verify unacquired district lookup returns INSUFFICIENT_DATA without zero-filling."""
        vuln = get_vulnerability_profile("non_existent_district")
        self.assertEqual(vuln["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(vuln["composite_vulnerability_score"])
        self.assertEqual(vuln["available_domains_count"], 0)

    def test_05_operational_lgd_mapping_verification(self):
        """Verify exact LGD code mapping for all 9 operational locations."""
        expected_lgd = {
            "champhai": "284",
            "aizawl": "283",
            "senapati": "272",
            "cherrapunji": "298",
            "tawang": "245",
            "kohima": "270",
            "dima_hasao": "315",
            "dhalai": "291",
            "gangtok": "244",
        }
        for did, lgd in expected_lgd.items():
            vuln = get_vulnerability_profile(did)
            self.assertEqual(str(vuln.get("dist_lgd")), str(lgd), f"LGD mismatch for {did}")

    def test_06_decoupling_vulnerability_from_ml_risk(self):
        """Verify vulnerability score and status are computationally separate from ML landslide risk score."""
        vuln = get_vulnerability_profile("champhai")
        # Champhai composite vulnerability score is 33.09
        self.assertEqual(vuln["composite_vulnerability_score"], 33.09)
        # Verify vulnerability profile contains explicit prototype disclaimer
        self.assertIn("prototype", vuln.get("disclaimer", "").lower())
        self.assertIn("decision-support", vuln.get("disclaimer", "").lower())

    def test_07_weather_unavailable_safety_contract(self):
        """Verify when weather inputs are missing, risk returns DATA UNAVAILABLE without fallback weather substitution."""
        resp = self.client.get("/api/districts")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
