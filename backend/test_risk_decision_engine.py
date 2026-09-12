"""Unit tests for NexSolve P6 Risk & Alert Decision Engine.

Verifies:
1. Low probability -> GREEN
2. Elevated probability -> YELLOW
3. High / Warning / Emergency probability -> ORANGE / RED
4. Missing weather gating -> DATA_UNAVAILABLE & null probability
5. Stale weather feed detection
6. Live weather feed detection
7. Null probability handling
8. Confidence unavailable when data missing
9. Reason code generation
10. Recommended action generation
11. Model version propagation
12. Policy version propagation
13. No historical fallback substitution
14. API compatibility for POST /api/risk
15. Frontend-compatible response fields
16. No automatic evacuation message
17. No fabricated reason codes
"""

from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.risk_decision_engine import evaluate_risk_decision, RiskDecision


class MockPrediction:
    def __init__(self, score=50.0, status="Moderate", confidence=62.0, model_id="candidate_a_rf_v1", model_version="1.1.0", feature_schema_version="v1"):
        self.score = score
        self.status = status
        self.confidence = confidence
        self.model_source = "NexSolve leakage-free RF"
        self.model_id = model_id
        self.model_version = model_version
        self.feature_schema_version = feature_schema_version
        self.factors = []


class TestRiskDecisionEngine(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.valid_weather = {
            "available": True,
            "is_live": True,
            "quality": "good",
            "data_age_hours": 0.5,
            "rainfall_1d": 20.0,
            "rainfall_3d": 40.0,
            "rainfall_7d": 60.0,
        }
        self.location = {
            "state": "Mizoram",
            "district": "Champhai District",
            "latitude": 23.4756,
            "longitude": 93.3289,
        }

    def test_01_low_probability_green(self):
        """Test low probability (< 0.35) maps to GREEN internal level."""
        pred = MockPrediction(score=20.0)
        dec = evaluate_risk_decision(pred, self.valid_weather, self.location)
        self.assertEqual(dec.risk_level, "GREEN")
        self.assertEqual(dec.risk_label, "Normal Risk")
        self.assertAlmostEqual(dec.risk_probability, 0.20)
        self.assertIn("MODEL_LOW_RISK", dec.reason_codes)

    def test_02_elevated_probability_yellow(self):
        """Test elevated probability (0.35 <= p < 0.50) maps to YELLOW internal level."""
        pred = MockPrediction(score=40.0)
        dec = evaluate_risk_decision(pred, self.valid_weather, self.location)
        self.assertEqual(dec.risk_level, "YELLOW")
        self.assertEqual(dec.risk_label, "Watch")
        self.assertAlmostEqual(dec.risk_probability, 0.40)
        self.assertIn("MODEL_ELEVATED_RISK", dec.reason_codes)

    def test_03_high_probability_orange_red(self):
        """Test probability >= 0.50 maps to ORANGE and >= 0.75 maps to RED."""
        pred_orange = MockPrediction(score=60.0)
        dec_orange = evaluate_risk_decision(pred_orange, self.valid_weather, self.location)
        self.assertEqual(dec_orange.risk_level, "ORANGE")
        self.assertEqual(dec_orange.risk_label, "Warning")

        pred_red = MockPrediction(score=85.0)
        dec_red = evaluate_risk_decision(pred_red, self.valid_weather, self.location)
        self.assertEqual(dec_red.risk_level, "RED")
        self.assertEqual(dec_red.risk_label, "Emergency Support")
        self.assertIn("MODEL_HIGH_RISK", dec_red.reason_codes)

    def test_04_missing_weather_gating(self):
        """Test missing weather feed produces DATA_UNAVAILABLE and null probability."""
        missing_weather = {"available": False, "rainfall_1d": None}
        dec = evaluate_risk_decision(MockPrediction(score=80.0), missing_weather, self.location)
        self.assertEqual(dec.risk_level, "DATA_UNAVAILABLE")
        self.assertIsNone(dec.risk_probability)
        self.assertEqual(dec.confidence, "UNAVAILABLE")
        self.assertEqual(dec.data_status, "UNAVAILABLE")
        self.assertEqual(dec.decision_status, "NOT_EVALUABLE")
        self.assertIn("WEATHER_FEED_UNAVAILABLE", dec.reason_codes)

    def test_05_stale_weather_detection(self):
        """Test stale weather dataset updates data_status to STALE and confidence to MEDIUM."""
        stale_weather = dict(self.valid_weather, quality="stale", data_age_hours=4.5)
        dec = evaluate_risk_decision(MockPrediction(score=30.0), stale_weather, self.location)
        self.assertEqual(dec.data_status, "STALE")
        self.assertEqual(dec.confidence, "MEDIUM")
        self.assertIn("WEATHER_FEED_STALE", dec.reason_codes)

    def test_06_live_weather_detection(self):
        """Test verified live weather dataset sets data_status to VERIFIED_LIVE and confidence to HIGH."""
        dec = evaluate_risk_decision(MockPrediction(score=30.0), self.valid_weather, self.location)
        self.assertEqual(dec.data_status, "VERIFIED_LIVE")
        self.assertEqual(dec.confidence, "HIGH")
        self.assertIn("WEATHER_FEED_LIVE", dec.reason_codes)

    def test_07_null_probability_handling(self):
        """Test decision engine handles None prediction gracefully."""
        dec = evaluate_risk_decision(None, self.valid_weather, self.location)
        self.assertEqual(dec.risk_level, "GREEN")
        self.assertEqual(dec.risk_probability, 0.0)

    def test_08_confidence_unavailable_when_data_missing(self):
        """Test confidence is UNAVAILABLE when live weather feed is missing."""
        dec = evaluate_risk_decision(None, None, self.location)
        self.assertEqual(dec.confidence, "UNAVAILABLE")
        self.assertEqual(dec.data_status, "UNAVAILABLE")

    def test_09_reason_code_generation(self):
        """Test reason codes are emitted based on rainfall threshold crossings."""
        heavy_weather = dict(self.valid_weather, rainfall_1d=60.0, rainfall_3d=110.0, rainfall_7d=210.0)
        dec = evaluate_risk_decision(MockPrediction(score=80.0), heavy_weather, self.location, extra_context={"date": "2026-07-15"})
        self.assertIn("RAIN_1D_ELEVATED", dec.reason_codes)
        self.assertIn("RAIN_3D_ELEVATED", dec.reason_codes)
        self.assertIn("RAIN_7D_ELEVATED", dec.reason_codes)
        self.assertIn("SEASONAL_FACTOR", dec.reason_codes)

    def test_10_recommended_action_generation(self):
        """Test authority recommendation generation for each risk level."""
        dec_green = evaluate_risk_decision(MockPrediction(score=10.0), self.valid_weather, self.location)
        self.assertIn("routine monitoring", dec_green.recommended_action.lower())

        dec_yellow = evaluate_risk_decision(MockPrediction(score=40.0), self.valid_weather, self.location)
        self.assertIn("increase monitoring", dec_yellow.recommended_action.lower())

        dec_orange = evaluate_risk_decision(MockPrediction(score=60.0), self.valid_weather, self.location)
        self.assertIn("prepare response resources", dec_orange.recommended_action.lower())

        dec_red = evaluate_risk_decision(MockPrediction(score=80.0), self.valid_weather, self.location)
        self.assertIn("escalate to authorized disaster-management personnel", dec_red.recommended_action.lower())

    def test_11_model_version_propagation(self):
        """Test model version metadata is propagated to decision object."""
        pred = MockPrediction(model_id="candidate_a_rf_v1", model_version="1.1.0", feature_schema_version="v1")
        dec = evaluate_risk_decision(pred, self.valid_weather, self.location)
        self.assertEqual(dec.model_id, "candidate_a_rf_v1")
        self.assertEqual(dec.model_version, "1.1.0")
        self.assertEqual(dec.feature_schema_version, "v1")

    def test_12_policy_version_propagation(self):
        """Test central policy version is propagated in decision object."""
        dec = evaluate_risk_decision(MockPrediction(score=30.0), self.valid_weather, self.location)
        self.assertEqual(dec.policy_version, "1.0.0-PROTOTYPE")

    def test_13_no_historical_fallback_substitution(self):
        """Test decision engine marks data UNAVAILABLE rather than silently using historical weather."""
        weather_historical = {"available": False, "is_live": False, "source": "IMD Historical NetCDF"}
        dec = evaluate_risk_decision(MockPrediction(score=70.0), weather_historical, self.location)
        self.assertEqual(dec.risk_level, "DATA_UNAVAILABLE")
        self.assertIsNone(dec.risk_probability)

    def test_14_api_compatibility(self):
        """Test POST /api/risk returns structured decision payload alongside prediction data."""
        res = self.client.post("/api/risk", json={
            "latitude": 23.4756,
            "longitude": 93.3289,
            "rainfall_1d": 65.0,
            "rainfall_3d": 120.0,
            "rainfall_7d": 220.0,
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("decision", data["data"])
        dec = data["data"]["decision"]
        self.assertIn("alertId", dec)
        self.assertIn("riskLevel", dec)
        self.assertIn("recommendedAction", dec)

    def test_15_frontend_compatible_response(self):
        """Test POST /api/risk preserves legacy riskScore, status, confidence, and factors keys."""
        res = self.client.post("/api/risk", json={
            "latitude": 23.4756,
            "longitude": 93.3289,
            "rainfall_1d": 10.0,
            "rainfall_3d": 20.0,
            "rainfall_7d": 30.0,
        })
        data = res.json()["data"]
        self.assertIn("riskScore", data)
        self.assertIn("status", data)
        self.assertIn("confidence", data)
        self.assertIn("factors", data)
        self.assertIn("modelSource", data)

    def test_16_no_automatic_evacuation_message(self):
        """Test recommended actions do NOT contain public evacuation commands."""
        dec_red = evaluate_risk_decision(MockPrediction(score=95.0), self.valid_weather, self.location)
        self.assertNotIn("public evacuation", dec_red.recommended_action.lower())
        self.assertNotIn("evacuate immediately", dec_red.recommended_action.lower())
        self.assertFalse(dec_red.is_official_warning)

    def test_17_no_fabricated_reason_codes(self):
        """Test reason codes are strictly backed by inputs (no elevated codes for zero rainfall)."""
        dry_weather = dict(self.valid_weather, rainfall_1d=0.0, rainfall_3d=0.0, rainfall_7d=0.0)
        dec = evaluate_risk_decision(MockPrediction(score=10.0), dry_weather, self.location, extra_context={"date": "2026-01-15"})
        self.assertNotIn("RAIN_1D_ELEVATED", dec.reason_codes)
        self.assertNotIn("RAIN_3D_ELEVATED", dec.reason_codes)
        self.assertNotIn("RAIN_7D_ELEVATED", dec.reason_codes)
        self.assertNotIn("SEASONAL_FACTOR", dec.reason_codes)


if __name__ == "__main__":
    unittest.main()
