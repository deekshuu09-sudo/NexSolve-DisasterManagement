"""Unit tests for P4 Feature Engineering Layer, Schema, and Leakage Controls.
"""

import hashlib
import json
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app, ROOT
from backend.services.feature_engineering_service import (
    extract_fused_features,
    get_spatial_boundary_info,
    get_inventory_context
)

class TestFeatureEngineeringLayer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_feature_schema_validity(self):
        """Verify feature_schema.json exists and is valid JSON."""
        schema_path = ROOT / "backend" / "data" / "features" / "feature_schema.json"
        self.assertTrue(schema_path.exists(), "feature_schema.json must exist")
        with open(schema_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["version"], "4.0.0")
        self.assertGreater(len(data["features"]), 10)

    def test_02_spatial_boundary_assignment(self):
        """Verify spatial point-in-polygon assignment against official SOI boundaries."""
        # Champhai coordinates (23.4756 N, 93.3289 E)
        res = get_spatial_boundary_info(23.4756, 93.3289)
        self.assertTrue(res["inside_ner"])
        self.assertEqual(res["state_name"], "Mizoram")
        self.assertEqual(res["district_name"], "Champhai")
        self.assertEqual(res["state_lgd"], 15)

    def test_03_inventory_target_exclusion(self):
        """Verify historical inventory metrics strictly exclude self-target slide_no."""
        # Target event from GSI inventory
        sample_slide = "ASM/HKN/83D07/2020/2"
        context_incl = get_inventory_context(25.2, 93.0, exclude_slide_no=None)
        context_excl = get_inventory_context(25.2, 93.0, exclude_slide_no=sample_slide)
        self.assertTrue(context_excl["target_excluded"])
        self.assertEqual(context_excl["total_ner_inventory_events"], context_incl["total_ner_inventory_events"])

    def test_04_missing_data_returns_null_not_zero(self):
        """Verify missing rainfall or coordinate data returns explicit null/unavailable."""
        fused = extract_fused_features(0.0, -140.0, rainfall_1d=None)
        self.assertFalse(fused["location"]["inside_ner"])
        self.assertEqual(fused["dynamic_weather"]["status"], "UNAVAILABLE")
        self.assertIsNone(fused["dynamic_weather"]["rainfall_1d"])

    def test_05_feature_endpoints(self):
        """Verify GET /api/features/schema and GET /api/features/{district_id} endpoints."""
        res_schema = self.client.get("/api/features/schema")
        self.assertEqual(res_schema.status_code, 200)
        self.assertEqual(res_schema.json()["version"], "4.0.0")

        res_feat = self.client.get("/api/features/champhai")
        self.assertEqual(res_feat.status_code, 200)
        data = res_feat.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["district_id"], "champhai")
        self.assertIn("fused_features", data)

    def test_06_ml_model_hash_unchanged(self):
        """Verify existing production model artifact is 100% unchanged."""
        model_path = ROOT / "backend" / "model" / "landslide_model.pkl"
        self.assertTrue(model_path.exists())
        with open(model_path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        expected_hash = "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1"
        self.assertEqual(h, expected_hash, "Production ML model hash must be unchanged before and after P4")

if __name__ == "__main__":
    unittest.main()
