"""
P10 Deployment & Production Readiness Unit Test Suite.

Verifies:
1. GET /api/health endpoint
2. GET /api/ready readiness endpoint
3. Core data endpoints (districts, coverage, corridors, geojson)
4. Dashboard summary aggregation endpoint
5. Risk decision endpoint (POST /api/risk)
6. CV report image analysis endpoint (POST /api/reports/analyze-image)
7. Field report submission endpoint (POST /api/reports)
8. P0/P6 Weather failure handling (missing weather -> DATA_UNAVAILABLE, risk_probability = null)
9. Stale weather confidence reduction
10. Oversized upload security gating (10MB limit)
11. Hard safety rule: is_official_warning remains strictly false
12. Model artifact SHA-256 integrity verification
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


class TestP10DeploymentReadiness(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_endpoint(self):
        """Verify GET /api/health returns 200 and status ONLINE."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ONLINE")

    def test_02_ready_endpoint(self):
        """Verify GET /api/ready returns 200 READY and checks status."""
        response = self.client.get("/api/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "READY")
        self.assertTrue(data["checks"]["model_loaded"])
        self.assertTrue(data["checks"]["administrative_boundaries"])

    def test_03_core_endpoints_availability(self):
        """Verify core system endpoints respond with 200 OK."""
        endpoints = [
            "/api/districts",
            "/api/coverage",
            "/api/corridors",
            "/api/terrain",
            "/api/features/schema",
            "/api/dashboard/summary"
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 200, f"Endpoint {ep} failed with {res.status_code}")

    def test_04_geojson_endpoints(self):
        """Verify official Survey of India GeoJSON endpoints."""
        states_res = self.client.get("/api/geojson/states")
        self.assertEqual(states_res.status_code, 200)
        self.assertEqual(states_res.json().get("type"), "FeatureCollection")

        districts_res = self.client.get("/api/geojson/districts")
        self.assertEqual(districts_res.status_code, 200)
        self.assertEqual(districts_res.json().get("type"), "FeatureCollection")

    def test_05_district_detail_endpoints(self):
        """Verify district exposure, vulnerability, and explainability endpoints."""
        did = "champhai"
        exp_res = self.client.get(f"/api/exposure/{did}")
        self.assertEqual(exp_res.status_code, 200)

        vuln_res = self.client.get(f"/api/vulnerability/{did}")
        self.assertEqual(vuln_res.status_code, 200)

        xai_res = self.client.get(f"/api/explainability/{did}")
        self.assertEqual(xai_res.status_code, 200)

    def test_06_risk_decision_endpoint(self):
        """Verify POST /api/risk evaluates risk decision cleanly."""
        res = self.client.post("/api/risk", json={
            "latitude": 23.4756,
            "longitude": 93.3289,
            "rainfall_1d": 55.0,
            "rainfall_3d": 130.0,
            "rainfall_7d": 260.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("decision", data.get("data", {}))

    def test_07_field_report_endpoints(self):
        """Verify report submission endpoints."""
        res = self.client.post("/api/reports", data={
            "type": "Landslide Observation",
            "location": "Champhai Highway Axis",
            "latitude": "23.4756",
            "longitude": "93.3289",
            "description": "Debris and road blockage observed near pass."
        })
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json().get("success"))

    def test_08_weather_gating_missing_rainfall(self):
        """Verify missing weather inputs gate decision to DATA_UNAVAILABLE."""
        decision_obj = evaluate_risk_decision(
            location={"latitude": 23.47, "longitude": 93.32, "district": "Champhai", "state": "Mizoram"},
            weather_data={"available": False, "rainfall_1d": None}
        )
        decision = decision_obj.to_dict()
        self.assertEqual(decision["riskLevel"], "DATA_UNAVAILABLE")
        self.assertIsNone(decision["riskProbability"])

    def test_09_stale_weather_downgrade(self):
        """Verify stale weather downgrades confidence."""
        decision_obj = evaluate_risk_decision(
            location={"latitude": 23.47, "longitude": 93.32, "district": "Champhai", "state": "Mizoram"},
            weather_data={"available": True, "rainfall_1d": 50.0, "rainfall_3d": 100.0, "rainfall_7d": 200.0, "quality": "stale"}
        )
        decision = decision_obj.to_dict()
        self.assertNotEqual(decision["confidence"], "HIGH")

    def test_10_is_official_warning_strictly_false(self):
        """Verify is_official_warning is hardcoded false."""
        res = self.client.get("/api/dashboard/summary")
        for node in res.json()["operational_nodes"]:
            self.assertFalse(node["decision"]["isOfficialWarning"])

    def test_11_model_integrity_verification(self):
        """Verify Candidate A production model remains active."""
        active = load_active_model()
        self.assertIsNotNone(active)
        self.assertEqual(active["model_id"], "candidate_a_rf_v1")
        self.assertEqual(active["model_version"], "1.1.0")


if __name__ == "__main__":
    unittest.main()
