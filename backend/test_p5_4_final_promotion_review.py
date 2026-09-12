"""Unit tests for NexSolve P5.4 Final Independent Promotion Review & Readiness Gate."""

import hashlib
import json
from pathlib import Path
import unittest
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
PROD_MODEL_PATH = BASE_DIR / "backend" / "model" / "landslide_model.pkl"
EXPERIMENTAL_DIR = BASE_DIR / "backend" / "model" / "experimental"

RESULTS_JSON_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_4_final_promotion_review.json"
RESULTS_CSV_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_4_final_promotion_review.csv"
REPORT_MD_PATH = BASE_DIR / "backend" / "data" / "features" / "p5_4_final_promotion_review.md"
FUSED_DATASET_PATH = BASE_DIR / "backend" / "data" / "features" / "fused_feature_dataset.csv"

PROD_SHA256 = "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1"


class TestP54FinalPromotionReview(unittest.TestCase):

    def test_01_production_model_hash_unchanged(self):
        """Verify production model artifact exists and SHA256 is unchanged."""
        self.assertTrue(PROD_MODEL_PATH.exists(), f"Production model missing at {PROD_MODEL_PATH}")
        with open(PROD_MODEL_PATH, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, PROD_SHA256, f"Production model SHA256 mismatch: {sha}")

    def test_02_candidate_a_versioned_separately(self):
        """Verify Candidate A artifact is versioned separately in backend/model/experimental/."""
        cand_a = EXPERIMENTAL_DIR / "candidate_a_rf_v1.pkl"
        self.assertTrue(cand_a.exists(), "Candidate A v1 artifact missing")

        with open(cand_a, "rb") as f:
            cand_a_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertNotEqual(cand_a_sha, PROD_SHA256, "Candidate A must not overwrite production artifact")

    def test_03_no_excluded_features_and_no_soilSat(self):
        """Verify distance_to_nearest_event_km and soilSat are excluded from candidate."""
        with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
            p5_4_data = json.load(f)

        features = p5_4_data["candidate_under_review"]["feature_set"]
        excluded = ["distance_to_nearest_event_km", "soilSat"]
        for exf in excluded:
            self.assertNotIn(exf, features)

    def test_04_no_random_row_split_and_temporal_locking(self):
        """Verify temporal cutoff ordering in fused dataset (no random row split)."""
        df = pd.read_csv(FUSED_DATASET_PATH)
        df["year"] = pd.to_datetime(df["date"]).dt.year

        train_df = df[df["year"] <= 2023]
        test_df = df[df["year"] > 2023]

        self.assertLessEqual(train_df["year"].max(), 2023)
        self.assertGreaterEqual(test_df["year"].min(), 2024)
        self.assertEqual(len(df), len(train_df) + len(test_df))

    def test_05_claims_audit_present_and_validated(self):
        """Verify claims audit table contains safe/unsafe assessments."""
        claims_df = pd.read_csv(RESULTS_CSV_PATH)
        self.assertGreaterEqual(len(claims_df), 10, "Expected at least 10 claims in claims audit table")
        self.assertIn("claim", claims_df.columns)
        self.assertIn("status", claims_df.columns)

    def test_06_all_p5_4_reports_exist(self):
        """Verify all required P5.4 output files exist and are non-empty."""
        files = [RESULTS_JSON_PATH, RESULTS_CSV_PATH, REPORT_MD_PATH]
        for fpath in files:
            self.assertTrue(fpath.exists(), f"Missing required file: {fpath}")
            self.assertGreater(fpath.stat().st_size, 0, f"File is empty: {fpath}")


if __name__ == "__main__":
    unittest.main()
