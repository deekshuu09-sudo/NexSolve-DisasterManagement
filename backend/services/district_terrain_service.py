"""District Terrain Summarization Service for NexSolve.

Computes spatial terrain statistics (elevation, slope, aspect, curvature metrics)
for all 131 official Survey of India districts in Northeast India.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
from shapely.geometry import shape, Point

BASE_DIR = Path(__file__).resolve().parents[2]
DISTRICT_GEOJSON_PATH = BASE_DIR / "backend" / "data" / "geojson" / "ner_districts_soi.geojson"
SUMMARY_CACHE_PATH = BASE_DIR / "backend" / "data" / "dem" / "processed" / "district_terrain_summary.json"

from backend.services.dem_service import _load_hgt_file, _get_pixel_coords, _calculate_slope, _calculate_aspect, _calculate_curvature

DISTRICT_TERRAIN_CACHE: Dict[str, Any] = {}

def process_single_district(feat, grid_sample_step: int = 25):
    props = feat["properties"]
    dist_id = props["district_id"]
    dist_name = props["district_name"]
    state_name = props["state_name"]
    
    geom = shape(feat["geometry"])
    min_lon, min_lat, max_lon, max_lat = geom.bounds

    lat_int_min, lat_int_max = int(math.floor(min_lat)), int(math.floor(max_lat))
    lon_int_min, lon_int_max = int(math.floor(min_lon)), int(math.floor(max_lon))

    elevations = []
    slopes = []
    aspects = []
    curvatures = []

    for lat_tile in range(lat_int_min, lat_int_max + 1):
        for lon_tile in range(lon_int_min, lon_int_max + 1):
            hgt_data = _load_hgt_file(lat_tile, lon_tile)
            if hgt_data is None:
                continue

            size = hgt_data.shape[0]
            
            tile_min_lat = max(min_lat, float(lat_tile))
            tile_max_lat = min(max_lat, float(lat_tile + 1.0))
            tile_min_lon = max(min_lon, float(lon_tile))
            tile_max_lon = min(max_lon, float(lon_tile + 1.0))

            r_start, c_end = _get_pixel_coords(hgt_data, tile_max_lat, tile_min_lon)
            r_end, c_start = _get_pixel_coords(hgt_data, tile_min_lat, tile_max_lon)

            r_min, r_max = min(r_start, r_end), max(r_start, r_end)
            c_min, c_max = min(c_start, c_end), max(c_start, c_end)

            for r in range(r_min, r_max + 1, grid_sample_step):
                for c in range(c_min, c_max + 1, grid_sample_step):
                    val = float(hgt_data[r, c])
                    if val == -32768 or val < -500 or val > 9000:
                        continue

                    lat_pt = (lat_tile + 1.0) - (r / (size - 1))
                    lon_pt = lon_tile + (c / (size - 1))

                    if geom.contains(Point(lon_pt, lat_pt)):
                        elevations.append(val)
                        if 1 <= r < size - 1 and 1 <= c < size - 1:
                            s = _calculate_slope(hgt_data, lat_pt, lon_pt)
                            a = _calculate_aspect(hgt_data, lat_pt, lon_pt)
                            cv = _calculate_curvature(hgt_data, lat_pt, lon_pt)
                            if s is not None: slopes.append(s)
                            if a is not None: aspects.append(a)
                            if cv is not None: curvatures.append(cv)

    if not elevations:
        return dist_id, {
            "district_id": dist_id,
            "district_name": dist_name,
            "state_name": state_name,
            "dist_lgd": props.get("dist_lgd"),
            "available": False,
            "source": "NASADEM 1 Arc-Second (~30m SRTM DEM)",
            "quality": "unavailable",
            "reason": "No valid DEM samples found inside district geometry"
        }

    elev_arr = np.array(elevations)
    slope_arr = np.array(slopes) if slopes else np.array([0.0])
    aspect_arr = np.array(aspects) if aspects else np.array([0.0])
    curv_arr = np.array(curvatures) if curvatures else np.array([0.0])

    counts = {"N": 0, "E": 0, "S": 0, "W": 0}
    for a in aspect_arr:
        if 315 <= a or a < 45: counts["N"] += 1
        elif 45 <= a < 135: counts["E"] += 1
        elif 135 <= a < 225: counts["S"] += 1
        else: counts["W"] += 1
    dom_aspect = max(counts, key=counts.get) if aspect_arr.size > 0 else "N/A"

    return dist_id, {
        "district_id": dist_id,
        "district_name": dist_name,
        "state_name": state_name,
        "dist_lgd": props.get("dist_lgd"),
        "available": True,
        "source": "NASADEM 1 Arc-Second (~30m SRTM DEM)",
        "quality": "valid",
        "sample_count": len(elevations),
        "elevation": {
            "min_m": round(float(np.min(elev_arr)), 1),
            "max_m": round(float(np.max(elev_arr)), 1),
            "mean_m": round(float(np.mean(elev_arr)), 1),
            "median_m": round(float(np.median(elev_arr)), 1)
        },
        "slope": {
            "mean_deg": round(float(np.mean(slope_arr)), 2),
            "max_deg": round(float(np.max(slope_arr)), 2),
            "p75_deg": round(float(np.percentile(slope_arr, 75)), 2),
            "p90_deg": round(float(np.percentile(slope_arr, 90)), 2)
        },
        "aspect": {
            "mean_deg": round(float(np.mean(aspect_arr)), 1),
            "dominant_quadrant": dom_aspect
        },
        "curvature": {
            "mean": round(float(np.mean(curv_arr)), 6),
            "min": round(float(np.min(curv_arr)), 6),
            "max": round(float(np.max(curv_arr)), 6)
        }
    }

def compute_district_terrain_summary() -> Dict[str, Any]:
    if not DISTRICT_GEOJSON_PATH.exists():
        return {}

    with open(DISTRICT_GEOJSON_PATH, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    features = geojson.get("features", [])
    print(f"Computing spatial terrain summary for {len(features)} districts using parallel threads...")

    results = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_single_district, feat) for feat in features]
        for future in as_completed(futures):
            dist_id, res = future.result()
            results[dist_id] = res

    SUMMARY_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    global DISTRICT_TERRAIN_CACHE
    DISTRICT_TERRAIN_CACHE = results
    print(f"District terrain summarization complete for {len(results)} districts. Saved to {SUMMARY_CACHE_PATH}")
    return results

def get_district_terrain_summary(district_id: str) -> Dict[str, Any]:
    global DISTRICT_TERRAIN_CACHE
    if not DISTRICT_TERRAIN_CACHE:
        if SUMMARY_CACHE_PATH.exists():
            with open(SUMMARY_CACHE_PATH, "r", encoding="utf-8") as f:
                DISTRICT_TERRAIN_CACHE = json.load(f)
        else:
            DISTRICT_TERRAIN_CACHE = compute_district_terrain_summary()

    if district_id in DISTRICT_TERRAIN_CACHE:
        return DISTRICT_TERRAIN_CACHE[district_id]

    return {
        "district_id": district_id,
        "available": False,
        "source": "NASADEM 1 Arc-Second (~30m SRTM DEM)",
        "quality": "unavailable",
        "reason": f"District ID '{district_id}' not found in terrain summary registry"
    }

if __name__ == "__main__":
    compute_district_terrain_summary()
