"""Unit tests for NASADEM / DEM terrain service and API endpoints in NexSolve.
"""

import unittest
import numpy as np
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.dem_service import (
    dem_data_available,
    get_elevation,
    get_slope,
    get_aspect,
    get_curvature,
    get_terrain_features,
    _get_elevation_from_hgt,
    _calculate_slope,
    _calculate_aspect,
    _calculate_curvature,
)
from backend.services.district_terrain_service import get_district_terrain_summary

class TestDEMTerrainService(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_dem_file_discovery(self):
        """Verify DEM data files are discovered."""
        self.assertTrue(dem_data_available(), "DEM files should be available locally")

    def test_02_elevation_extraction_valid_coordinate(self):
        """Verify elevation extraction for Champhai (known elevation ~1428m)."""
        elev = get_elevation(23.4756, 93.3289)
        self.assertIsNotNone(elev, "Elevation should not be None for valid coordinate")
        self.assertGreater(elev, 1000.0, "Champhai elevation should be > 1000m")

    def test_03_slope_aspect_curvature_calculation(self):
        """Verify derived slope, aspect, and curvature metrics."""
        slope = get_slope(23.4756, 93.3289)
        aspect = get_aspect(23.4756, 93.3289)
        curv = get_curvature(23.4756, 93.3289)

        self.assertIsNotNone(slope)
        self.assertIsNotNone(aspect)
        self.assertIsNotNone(curv)

        self.assertTrue(0 <= slope <= 90, "Slope degrees must be in range [0, 90]")
        self.assertTrue(0 <= aspect <= 360, "Aspect degrees must be in range [0, 360]")

    def test_04_missing_tile_returns_none_not_zero(self):
        """Verify missing DEM tile returns None/unavailable, NEVER silent zero."""
        # Coordinate in Pacific Ocean (no HGT tile)
        features = get_terrain_features(0.0, -140.0)
        self.assertFalse(features["available"])
        self.assertIsNone(features["elevation_m"])
        self.assertIsNone(features["slope_deg"])
        self.assertIsNone(features["aspect_deg"])
        self.assertIsNone(features["curvature"])
        self.assertEqual(features["quality"], "unavailable")

    def test_05_nodata_handling_returns_none_not_zero(self):
        """Verify NODATA (-32768) pixels return None, NOT zero."""
        dummy_hgt = np.full((3601, 3601), -32768, dtype=">i2")
        elev = _get_elevation_from_hgt(dummy_hgt, 23.5, 93.5)
        slope = _calculate_slope(dummy_hgt, 23.5, 93.5)
        aspect = _calculate_aspect(dummy_hgt, 23.5, 93.5)
        curv = _calculate_curvature(dummy_hgt, 23.5, 93.5)

        self.assertIsNone(elev, "NODATA pixel must return None for elevation")
        self.assertIsNone(slope, "NODATA neighborhood must return None for slope")
        self.assertIsNone(aspect, "NODATA neighborhood must return None for aspect")
        self.assertIsNone(curv, "NODATA neighborhood must return None for curvature")

    def test_06_district_terrain_summary_extraction(self):
        """Verify spatial district terrain summary returns multi-point statistics."""
        summary = get_district_terrain_summary("tawang")
        self.assertTrue(summary["available"])
        self.assertEqual(summary["district_name"], "Tawang")
        self.assertEqual(summary["state_name"], "Arunachal Pradesh")
        self.assertIn("elevation", summary)
        self.assertIn("slope", summary)
        self.assertIn("aspect", summary)
        self.assertIn("curvature", summary)
        self.assertGreater(summary["elevation"]["max_m"], summary["elevation"]["min_m"])

    def test_07_terrain_api_endpoints(self):
        """Verify GET /api/terrain and GET /api/terrain/{district_id} endpoints."""
        res_t = self.client.get("/api/terrain")
        self.assertEqual(res_t.status_code, 200)
        data_t = res_t.json()
        self.assertTrue(data_t["success"])
        self.assertTrue(data_t["available"])
        self.assertEqual(data_t["resolution"], "30m (1 arc-second)")

        res_td = self.client.get("/api/terrain/cherrapunji")
        self.assertEqual(res_td.status_code, 200)
        data_td = res_td.json()
        self.assertTrue(data_td["success"])
        self.assertTrue(data_td["point_terrain"]["available"])
        self.assertTrue(data_td["spatial_summary"]["available"])

if __name__ == "__main__":
    unittest.main()
