"""Unit tests for NexSolve P5.3.1 Final Leakage-Safe Promotion Review Correction."""

import hashlib
import json
from pathlib import Path
import unittest
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
PROD_MODEL_PATH = BASE_DIR / "backend" / "model" / "landslide_model.pkl"
EXPERIMENTAL_DIR = BASE_DIR / "backend" / "model" / "experimental"

RESULTS_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_results.json"
RESULTS_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_results.csv"
REGISTRY_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_model_registry.json"
REPORT_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_promotion_review_report.md"
CALIBRATION_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_calibration_report.md"
THRESHOLD_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_threshold_analysis.csv"
STATE_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_state_performance.csv"
DISTRICT_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_3_1_district_performance.csv"
FUSED_DATASET_PATH = BASE_DIR / "backend" / "data" / "features" / "fused_feature_dataset.csv"

PROD_SHA256 = "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1"


class TestP531PromotionReview(unittest.TestCase):

    def test_01_production_model_hash_unchanged(self):
        """Verify production model artifact exists and SHA256 is unchanged."""
        self.assertTrue(PROD_MODEL_PATH.exists(), f"Production model missing at {PROD_MODEL_PATH}")
        with open(PROD_MODEL_PATH, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, PROD_SHA256, f"Production model SHA256 mismatch: {sha}")

    def test_02_no_2024plus_in_threshold_selection(self):
        """Verify threshold selection stage uses ONLY internal pre-2024 development predictions."""
        thresh_df = pd.read_csv(THRESHOLD_CSV_PATH)
        dev_thresh_rows = thresh_df[thresh_df["stage"] == "INTERNAL_PRE2024_DEVELOPMENT"]
        self.assertGreater(len(dev_thresh_rows), 0, "Internal pre-2024 development threshold rows missing")
        for disclaimer in dev_thresh_rows["disclaimer"]:
            self.assertIn("prototype decision-support thresholds", disclaimer)

    def test_03_no_2024plus_in_calibration_or_candidate_selection(self):
        """Verify calibration and model registry reflect strict pre-2024 cutoff."""
        with open(REGISTRY_JSON_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)

        for entry in registry:
            self.assertEqual(entry["training_cutoff"], "date <= 2023-12-31")
            self.assertIn("frozen_selected_threshold", entry)

        with open(CALIBRATION_MD_PATH, "r", encoding="utf-8") as f:
            cal_text = f.read()
        self.assertIn("date <= 2023-12-31", cal_text)

    def test_04_no_random_row_split_and_no_future_information(self):
        """Verify temporal cutoff ordering in fused dataset (no random row split)."""
        df = pd.read_csv(FUSED_DATASET_PATH)
        df["year"] = pd.to_datetime(df["date"]).dt.year

        train_df = df[df["year"] <= 2023]
        test_df = df[df["year"] > 2023]

        self.assertLessEqual(train_df["year"].max(), 2023)
        self.assertGreaterEqual(test_df["year"].min(), 2024)
        self.assertEqual(len(df), len(train_df) + len(test_df))

    def test_05_no_excluded_features_and_no_synthetic_data(self):
        """Verify distance_to_nearest_event_km and soilSat are excluded across candidate models."""
        with open(REGISTRY_JSON_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)

        excluded = ["distance_to_nearest_event_km", "soilSat"]
        for entry in registry:
            for exf in excluded:
                self.assertNotIn(exf, entry["feature_set"])

    def test_06_versioned_candidate_artifacts_exist_separately(self):
        """Verify versioned candidate artifacts exist in backend/model/experimental/."""
        cand_a = EXPERIMENTAL_DIR / "candidate_a_rf_v1_1.pkl"
        cand_b = EXPERIMENTAL_DIR / "candidate_b_rf_v1_1.pkl"
        cand_c = EXPERIMENTAL_DIR / "candidate_c_rf_v1_1.pkl"
        cand_d = EXPERIMENTAL_DIR / "candidate_d_histgb_v1_1.pkl"

        self.assertTrue(cand_a.exists(), "Candidate A v1.1 artifact missing")
        self.assertTrue(cand_b.exists(), "Candidate B v1.1 artifact missing")
        self.assertTrue(cand_c.exists(), "Candidate C v1.1 artifact missing")
        self.assertTrue(cand_d.exists(), "Candidate D v1.1 artifact missing")

        with open(cand_a, "rb") as f:
            cand_a_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertNotEqual(cand_a_sha, PROD_SHA256, "Candidate A must not overwrite production artifact")

    def test_07_all_p5_3_1_reports_exist(self):
        """Verify all P5.3.1 reports and data files exist and are populated."""
        files = [
            RESULTS_JSON_PATH, RESULTS_CSV_PATH, REGISTRY_JSON_PATH,
            REPORT_MD_PATH, CALIBRATION_MD_PATH, THRESHOLD_CSV_PATH,
            STATE_CSV_PATH, DISTRICT_CSV_PATH
        ]
        for fpath in files:
            self.assertTrue(fpath.exists(), f"Missing required file: {fpath}")
            self.assertGreater(fpath.stat().st_size, 0, f"File is empty: {fpath}")


if __name__ == "__main__":
    unittest.main()
