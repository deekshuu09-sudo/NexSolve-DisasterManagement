"""Unit tests for NexSolve P8 Explainability & Decision-Support Layer.

Verifies:
1. Normal live-weather risk explainability generation
2. High-risk result explainability & non-causal explanation text
3. Low-risk result explainability
4. Missing rainfall input handling
5. Unavailable weather gating & risk_probability = null
6. Stale weather feed detection & confidence description
7. P7C vulnerability available context inclusion
8. P7C vulnerability unavailable context status
9. Local explanation availability flag (strictly False, no invented SHAP values)
10. Decoupling assertion: Risk probability and vulnerability score are NEVER merged/multiplied
11. is_official_warning flag remains strictly False
12. Existing API compatibility (POST /api/risk and GET /api/explainability/{district_id})
13. Original production model SHA256 preservation (landslide_model.pkl: d8546b0f7837...)
14. Promoted Candidate A model SHA256 preservation (candidate_a_rf_v1.pkl: 1acad34e85...)
15. Frozen P6 decision thresholds (0.35, 0.50, 0.75)
"""

import hashlib
import json
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.explainability_service import generate_explainability_report, get_model_feature_importances
from backend.services.risk_decision_engine import evaluate_risk_decision

ROOT = Path(__file__).resolve().parents[1]
LANDSLIDE_MODEL_PATH = ROOT / "backend" / "model" / "landslide_model.pkl"
CANDIDATE_A_PATH = ROOT / "backend" / "model" / "experimental" / "candidate_a_rf_v1.pkl"
RISK_POLICY_PATH = ROOT / "backend" / "data" / "config" / "risk_policy.json"


class TestP8Explainability(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_normal_live_weather_explainability(self):
        """Verify explainability generation for normal live weather inputs."""
        weather = {"available": True, "is_live": True, "quality": "good", "rainfall_1d": 25.0, "rainfall_3d": 45.0, "rainfall_7d": 70.0}
        decision = evaluate_risk_decision(
            model_prediction={"riskScore": 45.0, "status": "Moderate"},
            weather_data=weather,
            location={"state": "Mizoram", "district": "Champhai", "latitude": 23.4756, "longitude": 93.3289},
        )
        report = generate_explainability_report(risk_decision=decision, weather_data=weather)
        self.assertEqual(report["weather_status"], "LIVE")
        self.assertEqual(report["risk_level"], "YELLOW")
        self.assertIn("contributing_factors", report)
        self.assertTrue(len(report["contributing_factors"]) > 0)

    def test_02_high_risk_result_explainability(self):
        """Verify high-risk explainability contains conservative non-causal explanation text."""
        weather = {"available": True, "is_live": True, "quality": "good", "rainfall_1d": 150.0, "rainfall_3d": 250.0, "rainfall_7d": 350.0}
        decision = evaluate_risk_decision(
            model_prediction={"riskScore": 85.0, "status": "Critical"},
            weather_data=weather,
            location={"state": "Mizoram", "district": "Champhai", "latitude": 23.4756, "longitude": 93.3289},
        )
        report = generate_explainability_report(risk_decision=decision, weather_data=weather)
        self.assertEqual(report["risk_level"], "RED")
        self.assertIn("contributed to the model's high landslide hazard estimate", report["explanation_text"])

    def test_03_low_risk_result_explainability(self):
        """Verify low-risk result explainability format."""
        weather = {"available": True, "is_live": True, "quality": "good", "rainfall_1d": 2.0, "rainfall_3d": 5.0, "rainfall_7d": 10.0}
        decision = evaluate_risk_decision(
            model_prediction={"riskScore": 12.0, "status": "Low"},
            weather_data=weather,
            location={"state": "Sikkim", "district": "Gangtok", "latitude": 27.33, "longitude": 88.61},
        )
        report = generate_explainability_report(risk_decision=decision, weather_data=weather)
        self.assertEqual(report["risk_level"], "GREEN")
        self.assertIn("Low rainfall accumulation", report["explanation_text"])

    def test_04_missing_rainfall_handling(self):
        """Verify missing rainfall fields mark weather_status as UNAVAILABLE and risk_probability as None."""
        weather = {"available": False, "rainfall_1d": None, "rainfall_3d": None, "rainfall_7d": None}
        decision = evaluate_risk_decision(
            model_prediction=None,
            weather_data=weather,
            location={"latitude": 23.4756, "longitude": 93.3289},
        )
        report = generate_explainability_report(risk_decision=decision, weather_data=weather)
        self.assertEqual(report["weather_status"], "UNAVAILABLE")
        self.assertIsNone(report["risk_probability"])
        self.assertEqual(report["risk_level"], "DATA_UNAVAILABLE")

    def test_05_unavailable_weather_gating(self):
        """Verify unavailable weather gating preserves P6 safety rule."""
        res = self.client.post("/api/risk", json={"latitude": 23.4756, "longitude": 93.3289})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertIsNone(data["data"]["riskScore"])
        self.assertEqual(data["data"]["decision"]["riskLevel"], "DATA_UNAVAILABLE")
        self.assertIn("explainability", data["data"])

    def test_06_stale_weather_detection(self):
        """Verify stale weather marks weather_status = STALE and uncertainty = HIGH."""
        weather = {"available": True, "is_live": True, "quality": "stale", "data_age_hours": 5.0, "rainfall_1d": 30.0}
        decision = evaluate_risk_decision(
            model_prediction={"riskScore": 40.0, "status": "Moderate"},
            weather_data=weather,
            location={"latitude": 23.4756, "longitude": 93.3289},
        )
        report = generate_explainability_report(risk_decision=decision, weather_data=weather)
        self.assertEqual(report["weather_status"], "STALE")
        self.assertEqual(report["uncertainty"]["uncertainty_level"], "HIGH")

    def test_07_vulnerability_available_context(self):
        """Verify available P7C vulnerability context is cleanly formatted in explainability output."""
        vuln_profile = {
            "status": "COMPUTED",
            "confidence": "HIGH",
            "data_completeness_pct": 100.0,
            "composite_vulnerability_score": 33.09,
            "contributing_factors": [{"domain_key": "healthcare", "contribution_pct": 45.94}],
        }
        report = generate_explainability_report(risk_decision={}, vulnerability_profile=vuln_profile)
        v_ctx = report["vulnerability_context"]
        self.assertEqual(v_ctx["status"], "COMPUTED")
        self.assertEqual(v_ctx["composite_vulnerability_score"], 33.09)
        self.assertIn("strictly separate decision layers", v_ctx["decoupling_rule"])

    def test_08_vulnerability_unavailable_status(self):
        """Verify unacquired vulnerability profile outputs VULNERABILITY DATA INSUFFICIENT."""
        report = generate_explainability_report(risk_decision={}, vulnerability_profile=None)
        v_ctx = report["vulnerability_context"]
        self.assertEqual(v_ctx["status"], "INSUFFICIENT_DATA")
        self.assertEqual(v_ctx["display_message"], "VULNERABILITY DATA INSUFFICIENT")

    def test_09_local_explanation_availability_flag(self):
        """Verify local_explanation_available is strictly False with conservative rationale."""
        report = generate_explainability_report(risk_decision={})
        loc_exp = report["local_explanation"]
        self.assertFalse(loc_exp["local_explanation_available"])
        self.assertIn("Conservative decision support policy", loc_exp["rationale"])

    def test_10_decoupling_assertion_no_merged_score(self):
        """Verify risk probability and vulnerability score are NEVER combined into a single score."""
        report = generate_explainability_report(
            risk_decision={"riskProbability": 0.75, "riskLevel": "RED"},
            vulnerability_profile={"composite_vulnerability_score": 65.0, "status": "COMPUTED"},
        )
        self.assertEqual(report["risk_probability"], 0.75)
        self.assertEqual(report["vulnerability_context"]["composite_vulnerability_score"], 65.0)
        self.assertNotIn("official_combined_score", report)

    def test_11_is_official_warning_flag_remains_false(self):
        """Verify is_official_warning flag is strictly False."""
        report = generate_explainability_report(risk_decision={"riskLevel": "RED"})
        self.assertFalse(report["is_official_warning"])

    def test_12_api_explainability_endpoint(self):
        """Verify GET /api/explainability/{district_id} returns 200 OK with complete schema."""
        res = self.client.get("/api/explainability/champhai")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["district_id"], "champhai")
        self.assertIn("explainability", data)
        exp = data["explainability"]
        self.assertIn("human_verification_items", exp)
        self.assertIn("model_feature_importance", exp)

    def test_13_production_model_artifact_sha_unchanged(self):
        """Verify original production model landslide_model.pkl SHA256 remains d8546b0f78372c..."""
        with open(LANDSLIDE_MODEL_PATH, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1")

    def test_14_candidate_a_model_artifact_sha_unchanged(self):
        """Verify candidate_a_rf_v1.pkl artifact SHA256 remains 1acad34e85b53df0cb..."""
        with open(CANDIDATE_A_PATH, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, "1acad34e85b53df0cb68e5e81cd81d68066c4173792e65a51288b35557ba0f72")

    def test_15_p6_risk_decision_thresholds_frozen(self):
        """Verify P6 risk decision thresholds remain frozen at 0.35, 0.50, 0.75."""
        with open(RISK_POLICY_PATH, "r", encoding="utf-8") as f:
            policy = json.load(f)
        thresholds = policy.get("thresholds", {})
        self.assertEqual(thresholds.get("elevated_risk_threshold"), 0.35)
        self.assertEqual(thresholds.get("warning_risk_threshold"), 0.50)
        self.assertEqual(thresholds.get("emergency_risk_threshold"), 0.75)


if __name__ == "__main__":
    unittest.main()
