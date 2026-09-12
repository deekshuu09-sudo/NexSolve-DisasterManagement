"""Prediction Regression & Promotion Safety Unit Tests for NexSolve P5.5 Controlled Promotion."""

import hashlib
import json
from pathlib import Path
import unittest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(BASE_DIR))

from backend.main import app
from backend.services.model_loader import load_active_model, get_model_registry, rollback_to_previous_model
from backend.model.predictor import predict, reload_model_package

MODEL_DIR = BASE_DIR / "backend" / "model"
PROD_MODEL_PATH = MODEL_DIR / "landslide_model.pkl"
REGISTRY_PATH = MODEL_DIR / "model_registry.json"
ARCHIVE_PATH = MODEL_DIR / "archive" / "landslide_model_v_current.pkl"
EXPECTED_PREV_SHA = "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1"
PROD_FEATURES = [
    "latitude", "longitude", "rainfall_1d", "rainfall_3d",
    "rainfall_7d", "month_sin", "month_cos"
]


class TestP55ModelPromotion(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_active_model_loads_via_registry(self):
        """Verify active model loads cleanly via central model_loader service."""
        pkg = load_active_model()
        self.assertIsNotNone(pkg, "Active model package failed to load")
        self.assertEqual(pkg["model_id"], "candidate_a_rf_v1")
        self.assertEqual(pkg["model_version"], "1.1.0")

    def test_02_model_artifact_exists_and_sha_matches_registry(self):
        """Verify candidate artifact exists and SHA256 matches registry entry."""
        pkg = load_active_model()
        art_path = Path(pkg["artifact_path"])
        self.assertTrue(art_path.exists(), f"Artifact missing at {art_path}")
        with open(art_path, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, pkg["sha256"], "Artifact SHA256 mismatch with registry")

    def test_03_feature_list_matches_production_schema(self):
        """Verify model feature list matches exact 7 production features."""
        pkg = load_active_model()
        self.assertEqual(pkg["features"], PROD_FEATURES)

    def test_04_prediction_succeeds_and_returns_metadata(self):
        """Verify ML prediction succeeds and exposes model metadata."""
        pred = predict({
            "latitude": 23.7271,
            "longitude": 92.7176,
            "rainfall_1d": 100.0,
            "rainfall_3d": 150.0,
            "rainfall_7d": 200.0,
            "date": "2026-09-11"
        })
        self.assertGreater(pred.score, 0)
        self.assertIn(pred.status, ["Low", "Moderate", "High", "Critical"])
        self.assertEqual(pred.model_id, "candidate_a_rf_v1")
        self.assertEqual(pred.model_version, "1.1.0")

    def test_05_api_risk_response_compatibility(self):
        """Verify API /api/risk response format and version visibility."""
        res = self.client.post("/api/risk", json={
            "latitude": 23.7271,
            "longitude": 92.7176,
            "rainfall_1d": 80.0,
            "rainfall_3d": 120.0,
            "rainfall_7d": 160.0
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("riskScore", data["data"])
        self.assertIn("status", data["data"])
        self.assertIn("confidence", data["data"])
        self.assertIn("factors", data["data"])
        self.assertEqual(data["data"]["modelId"], "candidate_a_rf_v1")
        self.assertEqual(data["data"]["modelVersion"], "1.1.0")

    def test_06_missing_weather_remains_safe(self):
        """Verify null/missing weather data returns explicit unavailable status."""
        res = self.client.post("/api/risk", json={
            "latitude": 23.7271,
            "longitude": 92.7176,
            "rainfall_1d": None,
            "rainfall_3d": None,
            "rainfall_7d": None
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertIsNone(data["data"]["riskScore"])
        self.assertIn("UNAVAILABLE", data["data"]["status"])

    def test_07_rollback_artifact_verification(self):
        """Verify archived rollback artifact exists and SHA256 equals original production hash."""
        self.assertTrue(ARCHIVE_PATH.exists(), f"Rollback archive missing at {ARCHIVE_PATH}")
        with open(ARCHIVE_PATH, "rb") as f:
            arch_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(arch_sha, EXPECTED_PREV_SHA, f"Rollback archive SHA mismatch: {arch_sha}")

    def test_08_rollback_mechanism(self):
        """Verify 1-step rollback mechanism restores previous production model as ACTIVE."""
        reg_before = get_model_registry()
        self.assertEqual(reg_before["active_model_id"], "candidate_a_rf_v1")

        # Execute rollback test
        rollback_to_previous_model()
        pkg_roll = load_active_model()
        self.assertEqual(pkg_roll["model_id"], "previous_production_model_v0")
        self.assertEqual(pkg_roll["sha256"], EXPECTED_PREV_SHA)

        # Restore Candidate A active promotion state
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            reg = json.load(f)
        reg["active_model_id"] = "candidate_a_rf_v1"
        reg["active_model_version"] = "1.1.0"
        for m in reg["models"]:
            m["status"] = "ACTIVE" if m["model_id"] == "candidate_a_rf_v1" else "ROLLBACK"
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(reg, f, indent=2)

        reload_model_package()
        pkg_restored = load_active_model()
        self.assertEqual(pkg_restored["model_id"], "candidate_a_rf_v1")

    def test_09_no_excluded_features_in_candidate(self):
        """Verify distance_to_nearest_event_km and soilSat are excluded from Candidate A."""
        pkg = load_active_model()
        excluded = ["distance_to_nearest_event_km", "soilSat"]
        for exf in excluded:
            self.assertNotIn(exf, pkg["features"])


if __name__ == "__main__":
    unittest.main()
