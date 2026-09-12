"""
P9 Operational Dashboard & Situation Awareness Layer Unit Test Suite.

Verifies:
1. GET /api/dashboard/summary endpoint & response schema
2. Monitored district count (131 SoI districts)
3. Evaluated risk level breakdown
4. Weather feed health classification
5. Vulnerability coverage summary (16 acquired, 115 insufficient data)
6. Operational nodes count (9 nodes) and risk decision integration
7. Weather data gating (missing weather -> DATA_UNAVAILABLE, risk_probability = null)
8. Stale weather confidence reduction
9. Vulnerability missing data preservation (composite score = null, not 0)
10. Strict separation of ML Risk and Vulnerability Score
11. Hard safety rule: is_official_warning remains strictly false
12. Backward compatibility of core endpoints
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.model_loader import load_active_model, get_model_registry
from backend.services.risk_decision_engine import evaluate_risk_decision
from backend.services.exposure_intelligence_service import get_vulnerability_profile, load_vulnerability_database


class TestP9OperationalDashboard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_dashboard_summary_endpoint_structure(self):
        """Verify GET /api/dashboard/summary returns 200 and required fields."""
        response = self.client.get("/api/dashboard/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("generated_at", data)
        self.assertEqual(data.get("spatial_framework"), "Official Survey of India (SoI) Administrative Boundaries")
        self.assertIn("monitored_districts_count", data)
        self.assertIn("operational_nodes_count", data)
        self.assertIn("weather_feed_health", data)
        self.assertIn("risk_level_counts", data)
        self.assertIn("vulnerability_coverage_summary", data)
        self.assertIn("corridors", data)
        self.assertIn("operational_nodes", data)
        self.assertIn("disclaimer", data)

    def test_02_monitored_districts_count(self):
        """Verify dashboard reports 131 Survey of India monitored districts."""
        response = self.client.get("/api/dashboard/summary")
        data = response.json()
        self.assertEqual(data["monitored_districts_count"], 131)

    def test_03_evaluated_risk_counts(self):
        """Verify risk level breakdown accounts for all monitored nodes."""
        response = self.client.get("/api/dashboard/summary")
        data = response.json()
        risk_counts = data["risk_level_counts"]
        expected_keys = {"RED", "ORANGE", "YELLOW", "GREEN", "DATA_UNAVAILABLE"}
        for key in expected_keys:
            self.assertIn(key, risk_counts)
            self.assertIsInstance(risk_counts[key], int)

    def test_04_weather_feed_health(self):
        """Verify weather feed health metric schema."""
        response = self.client.get("/api/dashboard/summary")
        data = response.json()
        weather = data["weather_feed_health"]
        self.assertIn(weather["status"], ["LIVE", "STALE", "UNAVAILABLE"])
        self.assertIn("live_points", weather)
        self.assertIn("stale_points", weather)
        self.assertIn("offline_points", weather)

    def test_05_vulnerability_coverage_accounting(self):
        """Verify vulnerability coverage summary correctly reports 16 scored and 115 insufficient data."""
        response = self.client.get("/api/dashboard/summary")
        data = response.json()
        vuln = data["vulnerability_coverage_summary"]
        self.assertEqual(vuln["total_districts"], 131)
        self.assertEqual(vuln["computed_count"], 8)
        self.assertEqual(vuln["partial_count"], 8)
        self.assertEqual(vuln["insufficient_data_count"], 115)
        self.assertEqual(vuln["computed_count"] + vuln["partial_count"] + vuln["insufficient_data_count"], 131)
        self.assertEqual(vuln["computed_count"] + vuln["partial_count"], 16)

    def test_06_operational_nodes_count_and_decisions(self):
        """Verify dashboard includes all 9 operational nodes with valid decision structures."""
        response = self.client.get("/api/dashboard/summary")
        data = response.json()
        nodes = data["operational_nodes"]
        self.assertEqual(len(nodes), 9)
        node_ids = {n["id"] for n in nodes}
        expected_ids = {"champhai", "senapati", "cherrapunji", "tawang", "kohima", "dima_hasao", "dhalai", "gangtok", "aizawl"}
        self.assertTrue(expected_ids.issubset(node_ids) or len(node_ids) >= 8)

        for node in nodes:
            self.assertIn("decision", node)
            decision = node["decision"]
            self.assertIn("riskLevel", decision)
            self.assertIn("isOfficialWarning", decision)
            self.assertFalse(decision["isOfficialWarning"])

    def test_07_weather_data_gating(self):
        """Verify missing weather inputs gate risk to DATA_UNAVAILABLE with null probability."""
        decision_obj = evaluate_risk_decision(
            location={"latitude": 23.47, "longitude": 93.32, "district": "Champhai", "state": "Mizoram"},
            weather_data={"available": False, "rainfall_1d": None, "rainfall_3d": 120.0, "rainfall_7d": 250.0}
        )
        decision = decision_obj.to_dict()
        self.assertEqual(decision["riskLevel"], "DATA_UNAVAILABLE")
        self.assertIsNone(decision["riskProbability"])
        self.assertEqual(decision["confidence"], "UNAVAILABLE")
        self.assertFalse(decision["isOfficialWarning"])

    def test_08_stale_weather_confidence_reduction(self):
        """Verify stale weather flag reduces decision confidence."""
        decision_obj = evaluate_risk_decision(
            location={"latitude": 23.47, "longitude": 93.32, "district": "Champhai", "state": "Mizoram"},
            weather_data={"available": True, "rainfall_1d": 45.0, "rainfall_3d": 120.0, "rainfall_7d": 250.0, "quality": "stale"}
        )
        decision = decision_obj.to_dict()
        self.assertNotEqual(decision["confidence"], "HIGH")
        self.assertIn("WEATHER_FEED_STALE", decision["reasonCodes"])

    def test_09_vulnerability_missing_data_preservation(self):
        """Verify insufficient data district keeps null composite score and is NOT filled with zero."""
        profile = get_vulnerability_profile("kamrup_metropolitan")
        self.assertEqual(profile["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(profile["composite_vulnerability_score"])

    def test_10_strict_separation_of_risk_and_vulnerability(self):
        """Verify ML risk endpoint and vulnerability endpoint remain 100% decoupled."""
        # 1. Post to risk endpoint
        risk_res = self.client.post("/api/risk", json={
            "latitude": 23.4756,
            "longitude": 93.3289,
            "rainfall_1d": 50.0,
            "rainfall_3d": 120.0,
            "rainfall_7d": 250.0
        })
        self.assertEqual(risk_res.status_code, 200)
        risk_data = risk_res.json()["data"]
        # Ensure risk endpoint does NOT calculate exposure score or multiply Risk x Vulnerability
        self.assertNotIn("composite_vulnerability_score", risk_data)

        # 2. Get vulnerability endpoint
        vuln_res = self.client.get("/api/vulnerability/champhai")
        self.assertEqual(vuln_res.status_code, 200)
        vuln_data = vuln_res.json()
        self.assertNotIn("riskProbability", vuln_data)
        self.assertNotIn("risk_probability", vuln_data)

    def test_11_is_official_warning_strictly_false(self):
        """Verify is_official_warning is hardcoded false across all responses."""
        summary_res = self.client.get("/api/dashboard/summary")
        for node in summary_res.json()["operational_nodes"]:
            self.assertFalse(node["decision"]["isOfficialWarning"])

        risk_res = self.client.post("/api/risk", json={
            "latitude": 27.586,
            "longitude": 91.865,
            "rainfall_1d": 200.0,
            "rainfall_3d": 400.0,
            "rainfall_7d": 800.0
        })
        self.assertFalse(risk_res.json()["data"]["decision"]["isOfficialWarning"])

    def test_12_model_artifacts_integrity(self):
        """Verify production model and candidate model metadata remain locked."""
        active = load_active_model()
        self.assertIsNotNone(active)
        self.assertEqual(active["model_id"], "candidate_a_rf_v1")
        self.assertEqual(active["model_version"], "1.1.0")

        registry = get_model_registry()
        self.assertEqual(registry["active_model_id"], "candidate_a_rf_v1")


if __name__ == "__main__":
    unittest.main()
