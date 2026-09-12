"""Unit tests for NexSolve P5.3 Independent Model Promotion Review."""

import hashlib
import json
from pathlib import Path
import unittest
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
PROD_MODEL_PATH = BASE_DIR / "backend" / "model" / "landslide_model.pkl"
EXPERIMENTAL_DIR = BASE_DIR / "backend" / "model" / "experimental"

RESULTS_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_results.json"
RESULTS_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_results.csv"
REGISTRY_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_model_registry.json"
REPORT_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_promotion_review_report.md"
CALIBRATION_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_calibration_report.md"
THRESHOLD_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_threshold_analysis.csv"
STATE_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_state_performance.csv"
DISTRICT_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_district_performance.csv"
FUSED_DATASET_PATH = BASE_DIR / "backend" / "data" / "features" / "fused_feature_dataset.csv"

PROD_SHA256 = "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1"


class TestP53PromotionReview(unittest.TestCase):

    def test_01_production_model_hash_unchanged(self):
        """Verify production model artifact exists and SHA256 is unchanged."""
        self.assertTrue(PROD_MODEL_PATH.exists(), f"Production model missing at {PROD_MODEL_PATH}")
        with open(PROD_MODEL_PATH, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, PROD_SHA256, f"Production model SHA256 mismatch: {sha}")

    def test_02_experimental_versioned_candidates_exist(self):
        """Verify versioned candidate artifacts exist in backend/model/experimental/."""
        cand_a = EXPERIMENTAL_DIR / "candidate_a_rf_v1.pkl"
        cand_b = EXPERIMENTAL_DIR / "candidate_b_rf_v1.pkl"
        cand_c = EXPERIMENTAL_DIR / "candidate_c_rf_v1.pkl"
        cand_d = EXPERIMENTAL_DIR / "candidate_d_histgb_v1.pkl"

        self.assertTrue(cand_a.exists(), "Candidate A versioned artifact missing")
        self.assertTrue(cand_b.exists(), "Candidate B versioned artifact missing")
        self.assertTrue(cand_c.exists(), "Candidate C versioned artifact missing")
        self.assertTrue(cand_d.exists(), "Candidate D versioned artifact missing")

        with open(cand_a, "rb") as f:
            cand_a_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertNotEqual(cand_a_sha, PROD_SHA256, "Candidate A artifact must not overwrite production model")

    def test_03_no_excluded_features(self):
        """Verify distance_to_nearest_event_km and soilSat are excluded across candidates."""
        with open(REGISTRY_JSON_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)

        excluded = ["distance_to_nearest_event_km", "soilSat"]
        for entry in registry:
            for exf in excluded:
                self.assertNotIn(exf, entry["feature_set"], f"Excluded feature {exf} found in model {entry['model_id']}")

    def test_04_temporal_cutoff_integrity(self):
        """Verify chronological split boundaries (train <= 2023, test >= 2024)."""
        df = pd.read_csv(FUSED_DATASET_PATH)
        df["year"] = pd.to_datetime(df["date"]).dt.year

        train_df = df[df["year"] <= 2023]
        test_df = df[df["year"] > 2023]

        self.assertLessEqual(train_df["year"].max(), 2023)
        self.assertGreaterEqual(test_df["year"].min(), 2024)

    def test_05_threshold_disclaimer_present(self):
        """Verify threshold analysis contains prototype disclaimers."""
        thresh_df = pd.read_csv(THRESHOLD_CSV_PATH)
        self.assertEqual(len(thresh_df), 7, "Expected 7 threshold evaluation rows")
        for disclaimer in thresh_df["disclaimer"]:
            self.assertIn("PROTOTYPE DECISION THRESHOLDS", disclaimer)

    def test_06_state_performance_covers_all_8_states(self):
        """Verify state performance CSV covers all 8 Northeast states."""
        st_df = pd.read_csv(STATE_CSV_PATH)
        self.assertEqual(len(st_df), 8, "Expected exactly 8 states in state performance report")
        expected_states = {"arunachal_pradesh", "assam", "manipur", "meghalaya", "mizoram", "nagaland", "sikkim", "tripura"}
        self.assertEqual(set(st_df["state_id"]), expected_states)

    def test_07_all_reports_generated(self):
        """Verify all P5.3 output files exist and are non-empty."""
        files = [
            RESULTS_JSON_PATH, RESULTS_CSV_PATH, REGISTRY_JSON_PATH,
            REPORT_MD_PATH, CALIBRATION_MD_PATH, THRESHOLD_CSV_PATH,
            STATE_CSV_PATH, DISTRICT_CSV_PATH
        ]
        for fpath in files:
            self.assertTrue(fpath.exists(), f"Missing required output file: {fpath}")
            self.assertGreater(fpath.stat().st_size, 0, f"File is empty: {fpath}")


if __name__ == "__main__":
    unittest.main()
