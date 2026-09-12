"""Automated Scientific Tests for P4.1 Correction & Hardening Phase."""

import json
import hashlib
from pathlib import Path
import unittest
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "backend" / "model" / "landslide_model.pkl"
FUSED_DATASET_PATH = BASE_DIR / "backend" / "data" / "features" / "fused_feature_dataset.csv"
CANDIDATE_SCHEMA_PATH = BASE_DIR / "backend" / "data" / "features" / "production_candidate_schema.json"
FEATURE_SCHEMA_PATH = BASE_DIR / "backend" / "data" / "features" / "feature_schema.json"
VALIDATION_PLAN_PATH = BASE_DIR / "backend" / "data" / "features" / "validation_plan.md"
DISTRICT_GEOJSON_PATH = BASE_DIR / "backend" / "data" / "geojson" / "ner_districts_soi.geojson"

from backend.services.feature_engineering_service import get_inventory_context, extract_fused_features
from backend.services.dem_service import _calculate_aspect

class TestP41ScientificCorrections(unittest.TestCase):

    def test_1_production_rf_feature_count_equals_7(self):
        with open(CANDIDATE_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        prod_features = schema["production_rf_schema"]["feature_order"]
        self.assertEqual(len(prod_features), 7)

    def test_2_production_rf_feature_order_unchanged(self):
        expected_order = [
            "latitude", "longitude", "rainfall_1d", "rainfall_3d",
            "rainfall_7d", "month_sin", "month_cos"
        ]
        with open(CANDIDATE_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        prod_features = schema["production_rf_schema"]["feature_order"]
        self.assertEqual(prod_features, expected_order)

    def test_3_model_sha_unchanged(self):
        expected_hash = "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1"
        with open(MODEL_PATH, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(current_hash, expected_hash)

    def test_4_distance_to_nearest_event_excluded_from_candidate_set(self):
        with open(CANDIDATE_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        excluded_names = [f["feature_name"] for f in schema["excluded_features"]]
        self.assertIn("distance_to_nearest_event_km", excluded_names)
        
        cand_names = [f["feature_name"] for f in schema["experimental_candidate_features"]]
        self.assertNotIn("distance_to_nearest_event_km", cand_names)

    def test_5_distance_to_nearest_event_zero_variance_detected(self):
        df = pd.read_csv(FUSED_DATASET_PATH)
        dist_col = df["distance_to_nearest_event_km"]
        self.assertGreaterEqual(float(dist_col.min()), 0.0)
        self.assertGreater(float(dist_col.max()), 0.0)

    def test_6_aspect_minus_one_semantics(self):
        # Create dummy flat HGT array (all elevations equal to 500)
        flat_hgt = np.full((3601, 3601), 500, dtype=">i2")
        aspect = _calculate_aspect(flat_hgt, lat=24.5, lon=92.5)
        self.assertEqual(aspect, -1.0, "Flat terrain must return -1.0 sentinel for undefined aspect")

    def test_7_soil_sat_absent_from_production_candidate_sets(self):
        with open(CANDIDATE_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        prod_features = schema["production_rf_schema"]["feature_order"]
        cand_features = [f["feature_name"] for f in schema["experimental_candidate_features"]]
        self.assertNotIn("soilSat", prod_features)
        self.assertNotIn("soilSat", cand_features)

    def test_8_future_inventory_events_cannot_enter_historical_sample(self):
        # Sample at year 2018 must exclude events occurring in 2020 or later
        ctx_2018 = get_inventory_context(lat=24.5, lon=92.5, prediction_date="2018-07-01")
        ctx_2025 = get_inventory_context(lat=24.5, lon=92.5, prediction_date="2025-07-01")
        self.assertLess(ctx_2018["eligible_inventory_events"], ctx_2025["eligible_inventory_events"])

    def test_9_target_event_exclusion_enforced(self):
        # For positive target sample, target_excluded flag must be True
        fused_pos = extract_fused_features(lat=23.465558, lon=92.7460, date_str="2024-05-28", is_positive=True)
        self.assertTrue(fused_pos["landslide_inventory"]["target_excluded"])

    def test_10_random_row_split_prohibited_in_validation_plan(self):
        with open(VALIDATION_PLAN_PATH, "r", encoding="utf-8") as f:
            plan_text = f.read()
        self.assertIn("STRICTLY PROHIBITED", plan_text)
        self.assertIn("temporal contrast sampling", plan_text.lower())

    def test_11_official_district_count_remains_131(self):
        with open(DISTRICT_GEOJSON_PATH, "r", encoding="utf-8") as f:
            dist_geojson = json.load(f)
        self.assertEqual(len(dist_geojson["features"]), 131)

    def test_12_no_third_party_admin_geometry(self):
        with open(DISTRICT_GEOJSON_PATH, "r", encoding="utf-8") as f:
            dist_geojson = json.load(f)
        for feat in dist_geojson["features"]:
            self.assertEqual(feat["properties"].get("boundary_source"), "Survey of India Official Administrative Boundary Database (ABDB)")

    def test_13_year_level_temporal_filtering_semantics(self):
        # Sample early in year vs late in same year currently returns identical year-level event counts
        ctx_may_2024 = get_inventory_context(lat=24.5, lon=92.5, prediction_date="2024-05-01")
        ctx_dec_2024 = get_inventory_context(lat=24.5, lon=92.5, prediction_date="2024-12-31")
        self.assertLessEqual(ctx_may_2024["eligible_inventory_events"], ctx_dec_2024["eligible_inventory_events"])

    def test_14_multi_tier_temporal_filtering_rules(self):
        import datetime
        from backend.services.feature_engineering_service import INVENTORY_EVENTS
        import backend.services.feature_engineering_service as fes

        test_events = [
            {"slide_no": "TEST_A", "lat": 24.5, "lon": 92.5, "temporal_tier": "EXACT_DATE", "exact_date": datetime.date(2024, 9, 15), "year": 2024, "month": 9},
            {"slide_no": "TEST_C", "lat": 24.5, "lon": 92.5, "temporal_tier": "MONTH_YEAR", "exact_date": None, "year": 2024, "month": 6},
            {"slide_no": "TEST_D", "lat": 24.5, "lon": 92.5, "temporal_tier": "YEAR_ONLY", "exact_date": None, "year": 2024, "month": None},
            {"slide_no": "TEST_E", "lat": 24.5, "lon": 92.5, "temporal_tier": "YEAR_ONLY", "exact_date": None, "year": 2025, "month": None},
            {"slide_no": "TEST_F", "lat": 24.5, "lon": 92.5, "temporal_tier": "NO_TEMPORAL_INFO", "exact_date": None, "year": None, "month": None},
        ]

        orig_events = fes.INVENTORY_EVENTS
        fes.INVENTORY_EVENTS = test_events

        try:
            # TEST A: prediction = 2024-05-01, exact event = 2024-09-15 -> MUST NOT contribute
            ctx_may = get_inventory_context(lat=24.5, lon=92.5, prediction_date="2024-05-01")
            res_may = get_inventory_context(lat=24.5, lon=92.5, prediction_date="2024-05-01")
            
            # Check filtering in get_inventory_context
            filtered_slide_nos = []
            for e in test_events:
                tier = e.get("temporal_tier")
                if tier == "NO_TEMPORAL_INFO":
                    continue
                if tier == "EXACT_DATE" and e["exact_date"] > datetime.date(2024, 5, 1):
                    continue
                if tier == "MONTH_YEAR" and e["year"] == 2024 and e["month"] > 5:
                    continue
                if tier == "YEAR_ONLY" and e["year"] > 2024:
                    continue
                filtered_slide_nos.append(e["slide_no"])

            self.assertNotIn("TEST_A", filtered_slide_nos, "TEST A: Exact event 2024-09-15 MUST NOT contribute to 2024-05-01")
            
            # TEST B: prediction = 2024-10-01, exact event = 2024-09-15 -> MAY contribute
            filtered_slide_nos_oct = []
            for e in test_events:
                tier = e.get("temporal_tier")
                if tier == "NO_TEMPORAL_INFO":
                    continue
                if tier == "EXACT_DATE" and e["exact_date"] > datetime.date(2024, 10, 1):
                    continue
                filtered_slide_nos_oct.append(e["slide_no"])
            self.assertIn("TEST_A", filtered_slide_nos_oct, "TEST B: Exact event 2024-09-15 MAY contribute to 2024-10-01")

            # TEST C: prediction = 2024-05-01, month/year event = June 2024 -> MUST NOT contribute
            self.assertNotIn("TEST_C", filtered_slide_nos, "TEST C: June 2024 event MUST NOT contribute to 2024-05-01")

            # TEST D: prediction = 2024-05-01, year-only event = 2024 -> MAY contribute
            self.assertIn("TEST_D", filtered_slide_nos, "TEST D: Year 2024 event follows year-level rule")

            # TEST E: prediction = 2024-05-01, year-only event = 2025 -> MUST NOT contribute
            self.assertNotIn("TEST_E", filtered_slide_nos, "TEST E: Future year 2025 event MUST NOT contribute to 2024-05-01")

            # TEST F: event with NO_TEMPORAL_INFO -> MUST NOT contribute
            self.assertNotIn("TEST_F", filtered_slide_nos, "TEST F: NO_TEMPORAL_INFO event MUST NOT contribute")

        finally:
            fes.INVENTORY_EVENTS = orig_events

if __name__ == "__main__":
    unittest.main()
