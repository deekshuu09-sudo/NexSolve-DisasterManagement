import unittest
from fastapi.testclient import TestClient
from backend.main import app

class TestCanonicalCoverageAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_coverage_returns_all_8_states(self):
        response = self.client.get("/api/coverage")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data["success"])
        self.assertTrue(data["coverage_configured"])
        self.assertEqual(data["total_states"], 8)
        self.assertFalse(data["boundary_data_available"])

        expected_state_ids = {
            "arunachal_pradesh", "assam", "manipur", "meghalaya",
            "mizoram", "nagaland", "sikkim", "tripura"
        }
        actual_state_ids = {s["id"] for s in data["states"]}
        self.assertEqual(actual_state_ids, expected_state_ids)

        for state in data["states"]:
            self.assertFalse(state["boundary_available"])
            self.assertIsNone(state["geometry"])
            self.assertEqual(state["boundary_source"], "Survey of India (Pending Integration)")

    def test_get_districts_exposes_operational_point_type(self):
        response = self.client.get("/api/districts")
        self.assertEqual(response.status_code, 200)
        res = response.json()
        self.assertTrue(res["success"])
        districts = res["data"]
        self.assertGreater(len(districts), 0)
        
        for d in districts:
            self.assertIn("state_id", d)
            self.assertIn("point_type", d)
            self.assertIn("boundary_available", d)
            self.assertFalse(d["boundary_available"])

if __name__ == "__main__":
    unittest.main()
