#!/usr/bin/env python3
"""
Acquire and validate DEM / Terrain tiles for NexSolve's Northeast India coverage.
Source: USGS / NASA SRTM 1-arc-second (30m) Skadi HGT tiles via AWS Open Data Elevation repository.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import json
import math
import os
from pathlib import Path
import urllib.request
import hashlib
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[2]
DEM_RAW_DIR = BASE_DIR / "backend" / "data" / "dem" / "raw"
DEM_PROCESSED_DIR = BASE_DIR / "backend" / "data" / "dem" / "processed"
DEM_RAW_DIR.mkdir(parents=True, exist_ok=True)
DEM_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

STATE_GEOJSON = BASE_DIR / "backend" / "data" / "geojson" / "ner_states_soi.geojson"

def get_required_tile_coords():
    with open(STATE_GEOJSON, "r", encoding="utf-8") as f:
        s_data = json.load(f)

    all_min_lon, all_min_lat, all_max_lon, all_max_lat = 180.0, 90.0, -180.0, -90.0
    for feat in s_data["features"]:
        coords = feat["geometry"]["coordinates"]
        def extract_pts(c):
            if isinstance(c[0], (int, float)):
                yield c
            else:
                for sub in c:
                    yield from extract_pts(sub)
        for pt in extract_pts(coords):
            all_min_lon = min(all_min_lon, pt[0])
            all_min_lat = min(all_min_lat, pt[1])
            all_max_lon = max(all_max_lon, pt[0])
            all_max_lat = max(all_max_lat, pt[1])

    tile_coords = set()
    for lat_i in range(int(math.floor(all_min_lat)), int(math.floor(all_max_lat)) + 1):
        for lon_i in range(int(math.floor(all_min_lon)), int(math.floor(all_max_lon)) + 1):
            tile_coords.add((lat_i, lon_i))

    return sorted(tile_coords)

def process_single_tile(lat_lon):
    lat, lon = lat_lon
    lat_prefix = f"N{abs(lat):02d}" if lat >= 0 else f"S{abs(lat):02d}"
    lon_prefix = f"E{abs(lon):03d}" if lon >= 0 else f"W{abs(lon):03d}"
    
    hgt_filename = f"NASADEM_HGT_n{abs(lat):02d}e{abs(lon):03d}.hgt"
    hgt_path = DEM_RAW_DIR / hgt_filename
    
    url = f"https://elevation-tiles-prod.s3.amazonaws.com/skadi/{lat_prefix}/{lat_prefix}{lon_prefix}.hgt.gz"
    
    if not hgt_path.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "NexSolve-DEM-Fetcher/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                gz_data = resp.read()
            hgt_bytes = gzip.decompress(gz_data)
            with open(hgt_path, "wb") as f:
                f.write(hgt_bytes)
        except Exception as e:
            return {
                "tile_name": hgt_filename,
                "lat": lat,
                "lon": lon,
                "status": "FAILED",
                "error": str(e)
            }

    # Validate file
    file_size = hgt_path.stat().st_size
    with open(hgt_path, "rb") as f:
        hgt_content = f.read()

    sha256 = hashlib.sha256(hgt_content).hexdigest()

    if file_size == 25934402:
        shape = (3601, 3601)
        resolution = "1 arc-second (~30m)"
    elif file_size == 2884802:
        shape = (1201, 1201)
        resolution = "3 arc-seconds (~90m)"
    else:
        return {
            "tile_name": hgt_filename,
            "lat": lat,
            "lon": lon,
            "status": "CORRUPTED",
            "file_size": file_size
        }

    arr = np.frombuffer(hgt_content, dtype=">i2").reshape(shape)
    valid_mask = (arr != -32768)
    valid_pixels = int(np.sum(valid_mask))
    nodata_pixels = int(np.sum(~valid_mask))

    min_elev = float(np.min(arr[valid_mask])) if valid_pixels > 0 else None
    max_elev = float(np.max(arr[valid_mask])) if valid_pixels > 0 else None
    mean_elev = float(np.mean(arr[valid_mask])) if valid_pixels > 0 else None

    return {
        "tile_name": hgt_filename,
        "lat": lat,
        "lon": lon,
        "status": "VALID",
        "file_size": file_size,
        "sha256": sha256,
        "shape": shape,
        "resolution": resolution,
        "valid_pixels": valid_pixels,
        "nodata_pixels": nodata_pixels,
        "min_elevation_m": min_elev,
        "max_elevation_m": max_elev,
        "mean_elevation_m": mean_elev,
        "crs": "EPSG:4326 (WGS84)"
    }

def download_and_validate():
    tiles = get_required_tile_coords()
    print(f"Starting parallel acquisition of {len(tiles)} DEM tiles...")

    manifest = []
    success_count = 0
    failed_count = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_single_tile, t): t for t in tiles}
        for future in as_completed(futures):
            res = future.result()
            manifest.append(res)
            if res["status"] == "VALID":
                success_count += 1
                print(f"  [OK] {res['tile_name']} ({res['resolution']}) - Elev: [{res['min_elevation_m']}m, {res['max_elevation_m']}m]")
            else:
                failed_count += 1
                print(f"  [FAIL/MISSING] {res['tile_name']}: {res.get('error', res.get('status'))}")

    manifest.sort(key=lambda x: (x["lat"], x["lon"]))
    manifest_path = DEM_PROCESSED_DIR / "dem_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDEM Parallel Acquisition & Validation Complete!")
    print(f"  Success: {success_count} / {len(tiles)} tiles")
    print(f"  Failed/Missing: {failed_count} / {len(tiles)} tiles")
    print(f"  Manifest saved to {manifest_path}")

if __name__ == "__main__":
    download_and_validate()
