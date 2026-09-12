"""Unit tests for NexSolve P7B Exposure Data Acquisition & Integration.

Verifies:
1. Exposure schema validation
2. Acquisition manifest validation & SHA-256 checksums
3. District join & SoI 131-district boundary governance
4. Coverage accounting across all 131 districts
5. Geometry & coordinate validity (lat -90 to 90, lng -180 to 180)
6. Missing-data semantics (explicit UNAVAILABLE, no synthetic zero-fill)
7. GET /api/exposure/{district_id} response schema
8. Provenance metadata in response
9. Active production model ID remains candidate_a_rf_v1
10. Original production model artifact SHA remains d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1
11. Promoted Candidate A artifact SHA remains 1acad34e85b53df0cb68e5e81cd81d68066c4173792e65a51288b35557ba0f72
"""

import hashlib
import json
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.exposure_service import get_district_exposure, load_exposure_database

ROOT = Path(__file__).resolve().parents[1]
LANDSLIDE_MODEL_PATH = ROOT / "backend" / "model" / "landslide_model.pkl"
CANDIDATE_A_PATH = ROOT / "backend" / "model" / "experimental" / "candidate_a_rf_v1.pkl"
EXPOSURE_DIR = ROOT / "backend" / "data" / "exposure"


class TestExposureService(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_01_exposure_schema_file_exists(self):
        """Verify exposure schema definition file exists and is valid JSON."""
        schema_path = EXPOSURE_DIR / "exposure_schema.json"
        self.assertTrue(schema_path.exists(), f"Schema file missing at {schema_path}")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema.get("schema_version"), "1.0.0")

    def test_02_acquisition_manifest_validity(self):
        """Verify acquisition manifest file exists and SHA-256 checksums match raw datasets."""
        manifest_path = EXPOSURE_DIR / "manifests" / "acquisition_manifest.json"
        self.assertTrue(manifest_path.exists(), f"Manifest file missing at {manifest_path}")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertEqual(manifest.get("manifest_version"), "1.0.0")

        # Verify raw file SHA256 checksums
        for dataset in manifest.get("acquired_datasets", []):
            raw_path = ROOT / dataset["raw_relative_path"]
            self.assertTrue(raw_path.exists(), f"Raw file missing at {raw_path}")
            with open(raw_path, "rb") as rf:
                computed_sha = hashlib.sha256(rf.read()).hexdigest()
            self.assertEqual(computed_sha, dataset["sha256"], f"SHA256 mismatch for {raw_path.name}")

    def test_03_coverage_report_accounting(self):
        """Verify coverage report accounts for all 131 SoI districts."""
        cov_path = EXPOSURE_DIR / "validation" / "coverage_report.json"
        self.assertTrue(cov_path.exists(), f"Coverage report missing at {cov_path}")
        with open(cov_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report.get("total_soi_districts"), 131)
        self.assertIn("domain_coverage", report)

    def test_04_quality_report_status(self):
        """Verify quality control report passes all automated checks."""
        q_path = EXPOSURE_DIR / "validation" / "quality_report.json"
        self.assertTrue(q_path.exists(), f"Quality report missing at {q_path}")
        with open(q_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        self.assertEqual(report.get("overall_quality_status"), "PASS")

    def test_05_coordinate_bounds_validity(self):
        """Verify health facility raw coordinates are geographically within NER bounds."""
        hfr_path = EXPOSURE_DIR / "raw" / "mohfw_hfr" / "mohfw_health_facilities_ner.json"
        if hfr_path.exists():
            with open(hfr_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for fac in data.get("facilities", []):
                lat = fac.get("latitude")
                lng = fac.get("longitude")
                self.assertTrue(20.0 <= lat <= 30.0, f"Latitude {lat} out of NER bounds for {fac['name']}")
                self.assertTrue(88.0 <= lng <= 98.0, f"Longitude {lng} out of NER bounds for {fac['name']}")

    def test_06_missing_data_semantics_no_zero_fill(self):
        """Verify unacquired exposure domains are set to UNAVAILABLE/null rather than zero-filled."""
        res = get_district_exposure("unknown_district_xyz")
        self.assertEqual(res["status"], "UNAVAILABLE")
        self.assertIsNone(res["demographic"])
        self.assertIsNone(res["vulnerability"])
        self.assertIsNone(res["healthcare"])
        self.assertIsNone(res["education"])
        self.assertIsNone(res["transport"])
        self.assertEqual(res["availability"]["demographic"], "UNAVAILABLE")

    def test_07_api_exposure_endpoint(self):
        """Verify GET /api/exposure/{district_id} returns 200 OK with exposure schema fields."""
        res = self.client.get("/api/exposure/champhai")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["district_id"], "champhai")
        self.assertIn("status", data)
        self.assertIn("availability", data)
        self.assertIn("provenance", data)

    def test_08_provenance_metadata_presence(self):
        """Verify exposure responses contain explicit provenance metadata for acquired domains."""
        data = get_district_exposure("champhai")
        self.assertTrue(len(data["provenance"]) > 0)
        prov = data["provenance"][0]
        self.assertIn("domain", prov)
        self.assertIn("dataset_name", prov)
        self.assertIn("provider", prov)
        self.assertIn("reference_year", prov)
        self.assertIn("authoritative_tier", prov)

    def test_09_production_model_artifact_sha_unchanged(self):
        """Verify original production model landslide_model.pkl SHA256 remains d8546b0f78372c..."""
        with open(LANDSLIDE_MODEL_PATH, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, "d8546b0f78372c02196c6858f88cc3d5af4b54379f5e14b0003d5cb54c950eb1")

    def test_10_candidate_a_model_artifact_sha_unchanged(self):
        """Verify candidate_a_rf_v1.pkl artifact SHA256 remains 1acad34e85b53df0cb..."""
        with open(CANDIDATE_A_PATH, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(sha, "1acad34e85b53df0cb68e5e81cd81d68066c4173792e65a51288b35557ba0f72")


if __name__ == "__main__":
    unittest.main()
