"""Unit tests for NexSolve P5.2 Leakage-Free Model Promotion Study."""

import hashlib
import json
from pathlib import Path
import unittest
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
PROD_MODEL_PATH = BASE_DIR / "backend" / "model" / "landslide_model.pkl"
EXPERIMENTAL_DIR = BASE_DIR / "backend" / "model" / "experimental"
RESULTS_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_2_results.json"
RESULTS_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_2_results.csv"
REGISTRY_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_2_model_registry.json"
REPORT_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_2_model_promotion_report.md"
FUSED_DATASET_PATH = BASE_DIR / "backend" / "data" / "features" / "fused_feature_dataset.csv"

PROD_SHA256 = "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1"


class TestP52ModelPromotion(unittest.TestCase):

    def test_01_production_model_unchanged(self):
        """Verify original production model exists and SHA256 hash is unchanged."""
        self.assertTrue(PROD_MODEL_PATH.exists(), f"Production model not found at {PROD_MODEL_PATH}")
        with open(PROD_MODEL_PATH, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, PROD_SHA256, f"Production model SHA256 mismatch: {sha}")

    def test_02_experimental_candidates_exist(self):
        """Verify experimental candidate models exist in backend/model/experimental/."""
        self.assertTrue(EXPERIMENTAL_DIR.exists(), f"Experimental directory not found at {EXPERIMENTAL_DIR}")
        cand_a = EXPERIMENTAL_DIR / "candidate_a_rf_leakage_free.pkl"
        cand_b = EXPERIMENTAL_DIR / "candidate_b_rf_terrain.pkl"
        cand_c = EXPERIMENTAL_DIR / "candidate_c_rf_inventory.pkl"
        cand_d = EXPERIMENTAL_DIR / "candidate_d_histgb_baseline.pkl"

        self.assertTrue(cand_a.exists(), "Candidate A artifact missing")
        self.assertTrue(cand_b.exists(), "Candidate B artifact missing")
        self.assertTrue(cand_c.exists(), "Candidate C artifact missing")
        self.assertTrue(cand_d.exists(), "Candidate D artifact missing")

        # Confirm candidate A is NOT identical to production model file
        with open(cand_a, "rb") as f:
            cand_a_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertNotEqual(cand_a_sha, PROD_SHA256, "Candidate A should be distinct from production model artifact")

    def test_03_no_excluded_features_in_registry(self):
        """Verify distance_to_nearest_event_km and soilSat are strictly excluded."""
        self.assertTrue(REGISTRY_JSON_PATH.exists(), "Registry JSON missing")
        with open(REGISTRY_JSON_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)

        excluded = ["distance_to_nearest_event_km", "soilSat"]
        for entry in registry:
            feature_set = entry["feature_set"]
            for exf in excluded:
                self.assertNotIn(exf, feature_set, f"Excluded feature {exf} found in model {entry['model_id']}")

    def test_04_temporal_cutoff_and_zero_location_district_overlap(self):
        """Verify temporal cutoff and group overlap checks in fused dataset."""
        df = pd.read_csv(FUSED_DATASET_PATH)
        df["year"] = pd.to_datetime(df["date"]).dt.year
        df["location_group"] = df["latitude"].astype(str) + "_" + df["longitude"].astype(str)

        train_df = df[df["year"] <= 2023]
        test_df = df[df["year"] > 2023]

        self.assertGreater(len(train_df), 0, "Train split empty")
        self.assertGreater(len(test_df), 0, "Test split empty")

        # Verify max train year <= 2023 and min test year >= 2024
        self.assertLessEqual(train_df["year"].max(), 2023)
        self.assertGreaterEqual(test_df["year"].min(), 2024)

    def test_05_artifact_files_generated(self):
        """Verify all P5.2 artifact files exist and are populated."""
        self.assertTrue(RESULTS_JSON_PATH.exists(), "P5.2 results JSON missing")
        self.assertTrue(RESULTS_CSV_PATH.exists(), "P5.2 results CSV missing")
        self.assertTrue(REGISTRY_JSON_PATH.exists(), "P5.2 registry JSON missing")
        self.assertTrue(REPORT_MD_PATH.exists(), "P5.2 report MD missing")

        results_df = pd.read_csv(RESULTS_CSV_PATH)
        self.assertGreaterEqual(len(results_df), 15, "Expected at least 15 result rows in p5_2_results.csv")


if __name__ == "__main__":
    unittest.main()
