"""DEM (Digital Elevation Model) service for terrain feature extraction.

Supports loading NASADEM / SRTM HGT files (1 arc-second 3601x3601 or 3 arc-second 1201x1201)
and extracting elevation, slope, aspect, and curvature for NexSolve's operational geography.
Falls back gracefully with explicit null/unavailable states if DEM files are not available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import math
import numpy as np

# Candidate data directories
BASE_DIR = Path(__file__).resolve().parents[2]
DEM_DIRS = [
    BASE_DIR / "backend" / "data" / "dem" / "raw",
    BASE_DIR / "backend" / "data" / "dem",
    BASE_DIR / "backend" / "data" / "DEM",
]


def _get_hgt_filename(lat: float, lon: float) -> str:
    """Get NASADEM / SRTM HGT filename for a given latitude/longitude.
    
    Format: NASADEM_HGT_nXXeYYY.hgt or NXXEYYY.hgt
    """
    lat_int = int(math.floor(lat))
    lon_int = int(math.floor(lon))
    
    lat_str_lower = f"n{abs(lat_int):02d}" if lat_int >= 0 else f"s{abs(lat_int):02d}"
    lon_str_lower = f"e{abs(lon_int):03d}" if lon_int >= 0 else f"w{abs(lon_int):03d}"
    
    return f"NASADEM_HGT_{lat_str_lower}{lon_str_lower}.hgt"


def _load_hgt_file(lat: float, lon: float) -> Optional[np.ndarray]:
    """Load a NASADEM HGT file and return as numpy array (1201x1201 or 3601x3601).
    
    Returns None if file is not found or corrupted.
    """
    lat_int = int(math.floor(lat))
    lon_int = int(math.floor(lon))
    
    lat_str_lower = f"n{abs(lat_int):02d}" if lat_int >= 0 else f"s{abs(lat_int):02d}"
    lon_str_lower = f"e{abs(lon_int):03d}" if lon_int >= 0 else f"w{abs(lon_int):03d}"
    
    lat_str_upper = f"N{abs(lat_int):02d}" if lat_int >= 0 else f"S{abs(lat_int):02d}"
    lon_str_upper = f"E{abs(lon_int):03d}" if lon_int >= 0 else f"W{abs(lon_int):03d}"

    possible_filenames = [
        f"NASADEM_HGT_{lat_str_lower}{lon_str_lower}.hgt",
        f"NASADEM_HGT_{lat_str_upper}{lon_str_upper}.hgt",
        f"{lat_str_upper}{lon_str_upper}.hgt",
        f"{lat_str_lower}{lon_str_lower}.hgt",
    ]

    for d in DEM_DIRS:
        if not d.exists():
            continue
        
        for fname in possible_filenames:
            filepath = d / fname
            if filepath.exists():
                try:
                    file_size = filepath.stat().st_size
                    if file_size == 25934402: # 3601 x 3601 int16
                        shape = (3601, 3601)
                    elif file_size == 2884802: # 1201 x 1201 int16
                        shape = (1201, 1201)
                    else:
                        continue
                        
                    with open(filepath, "rb") as f:
                        data = f.read()
                    elevations = np.frombuffer(data, dtype=">i2").reshape(shape)
                    return elevations
                except Exception as e:
                    print(f"Error loading HGT file {filepath}: {e}")
                    
        # Check zip archives
        import zipfile
        for zname in possible_filenames:
            stem = zname.replace(".hgt", "")
            zip_candidates = list(d.glob(f"*{stem}*.zip"))
            for zpath in zip_candidates:
                try:
                    with zipfile.ZipFile(zpath, "r") as zf:
                        for zmember in zf.namelist():
                            if zmember.endswith(".hgt"):
                                data = zf.read(zmember)
                                if len(data) == 25934402:
                                    return np.frombuffer(data, dtype=">i2").reshape((3601, 3601))
                                elif len(data) == 2884802:
                                    return np.frombuffer(data, dtype=">i2").reshape((1201, 1201))
                except Exception:
                    pass

    return None


def _get_pixel_coords(hgt_data: np.ndarray, lat: float, lon: float) -> Tuple[int, int]:
    """Convert lat/lon to row/col pixel indices for HGT array."""
    size = hgt_data.shape[0]
    lat_int = int(math.floor(lat))
    lon_int = int(math.floor(lon))
    
    lat_offset = lat - lat_int
    lon_offset = lon - lon_int
    
    row = int((1.0 - lat_offset) * (size - 1))
    col = int(lon_offset * (size - 1))
    
    row = max(0, min(size - 1, row))
    col = max(0, min(size - 1, col))
    
    return row, col


def _get_ground_spacing_m(lat: float, size: int) -> Tuple[float, float]:
    """Calculate ground spacing (dx, dy) in meters per pixel based on latitude and grid size.
    
    1 degree of latitude ≈ 111,320 meters.
    1 degree of longitude ≈ 111,320 * cos(lat_radians) meters.
    """
    grid_cells = size - 1
    dy = 111320.0 / grid_cells
    dx = (111320.0 * math.cos(math.radians(lat))) / grid_cells
    return dx, dy


def _get_elevation_from_hgt(hgt_data: np.ndarray, lat: float, lon: float) -> Optional[float]:
    """Extract elevation in meters from HGT array.
    
    Returns None if coordinate is invalid or NODATA (-32768).
    """
    row, col = _get_pixel_coords(hgt_data, lat, lon)
    elevation = float(hgt_data[row, col])
    
    if elevation == -32768 or elevation < -500 or elevation > 9000:
        return None
        
    return elevation


def _calculate_slope(hgt_data: np.ndarray, lat: float, lon: float) -> Optional[float]:
    """Calculate slope in degrees (0-90) using 3x3 Sobel operator with latitude-scaled cell dimensions."""
    row, col = _get_pixel_coords(hgt_data, lat, lon)
    size = hgt_data.shape[0]
    
    row = max(1, min(size - 2, row))
    col = max(1, min(size - 2, col))
    
    neighborhood = hgt_data[row - 1 : row + 2, col - 1 : col + 2].astype(float)
    
    if np.any(neighborhood == -32768):
        return None
        
    dx_m, dy_m = _get_ground_spacing_m(lat, size)
    
    # Sobel kernels
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
    
    dz_dx = np.sum(neighborhood * sobel_x) / (8.0 * dx_m)
    dz_dy = np.sum(neighborhood * sobel_y) / (8.0 * dy_m)
    
    slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg = math.degrees(slope_rad)
    
    return max(0.0, min(90.0, slope_deg))


def _calculate_aspect(hgt_data: np.ndarray, lat: float, lon: float) -> Optional[float]:
    """Calculate aspect (direction of steepest slope) in degrees (0-360, where 0=North)."""
    row, col = _get_pixel_coords(hgt_data, lat, lon)
    size = hgt_data.shape[0]
    
    row = max(1, min(size - 2, row))
    col = max(1, min(size - 2, col))
    
    neighborhood = hgt_data[row - 1 : row + 2, col - 1 : col + 2].astype(float)
    
    if np.any(neighborhood == -32768):
        return None
        
    dx_m, dy_m = _get_ground_spacing_m(lat, size)
    
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
    
    dz_dx = np.sum(neighborhood * sobel_x) / (8.0 * dx_m)
    dz_dy = np.sum(neighborhood * sobel_y) / (8.0 * dy_m)
    
    if abs(dz_dx) < 1e-7 and abs(dz_dy) < 1e-7:
        return -1.0 # Flat terrain / undefined aspect sentinel
        
    # aspect = atan2(dz_dy, -dz_dx)
    aspect_rad = math.atan2(dz_dy, -dz_dx)
    aspect_deg = math.degrees(aspect_rad)
    
    # Convert to 0-360 degrees where 0 = North
    compass_deg = (90.0 - aspect_deg) % 360.0
    return compass_deg


def _calculate_curvature(hgt_data: np.ndarray, lat: float, lon: float) -> Optional[float]:
    """Calculate 5-point discrete Laplacian profile curvature (1/m)."""
    row, col = _get_pixel_coords(hgt_data, lat, lon)
    size = hgt_data.shape[0]
    
    row = max(1, min(size - 2, row))
    col = max(1, min(size - 2, col))
    
    neighborhood = hgt_data[row - 1 : row + 2, col - 1 : col + 2].astype(float)
    
    if np.any(neighborhood == -32768):
        return None
        
    dx_m, dy_m = _get_ground_spacing_m(lat, size)
    
    center = neighborhood[1, 1]
    d2z_dx2 = (neighborhood[1, 2] - 2.0 * center + neighborhood[1, 0]) / (dx_m ** 2)
    d2z_dy2 = (neighborhood[0, 1] - 2.0 * center + neighborhood[2, 1]) / (dy_m ** 2)
    
    laplacian = d2z_dx2 + d2z_dy2
    return float(laplacian)


def get_elevation(lat: float, lon: float) -> Optional[float]:
    hgt_data = _load_hgt_file(lat, lon)
    if hgt_data is None:
        return None
    return _get_elevation_from_hgt(hgt_data, lat, lon)


def get_slope(lat: float, lon: float) -> Optional[float]:
    hgt_data = _load_hgt_file(lat, lon)
    if hgt_data is None:
        return None
    return _calculate_slope(hgt_data, lat, lon)


def get_aspect(lat: float, lon: float) -> Optional[float]:
    hgt_data = _load_hgt_file(lat, lon)
    if hgt_data is None:
        return None
    return _calculate_aspect(hgt_data, lat, lon)


def get_curvature(lat: float, lon: float) -> Optional[float]:
    hgt_data = _load_hgt_file(lat, lon)
    if hgt_data is None:
        return None
    return _calculate_curvature(hgt_data, lat, lon)


def get_terrain_features(lat: float, lon: float) -> Dict[str, Any]:
    """Get all terrain features at given lat/lon.
    
    Returns explicit status, source, elevation, slope, aspect, curvature, and quality.
    """
    hgt_data = _load_hgt_file(lat, lon)
    if hgt_data is None:
        return {
            "available": False,
            "source": "NASADEM 1 Arc-Second (~30m SRTM DEM)",
            "elevation_m": None,
            "slope_deg": None,
            "aspect_deg": None,
            "curvature": None,
            "quality": "unavailable",
            "reason": "DEM tile file not found for coordinates"
        }
        
    elev = _get_elevation_from_hgt(hgt_data, lat, lon)
    if elev is None:
        return {
            "available": False,
            "source": "NASADEM 1 Arc-Second (~30m SRTM DEM)",
            "elevation_m": None,
            "slope_deg": None,
            "aspect_deg": None,
            "curvature": None,
            "quality": "nodata",
            "reason": "Coordinate falls in NODATA/void pixel"
        }

    slope = _calculate_slope(hgt_data, lat, lon)
    aspect = _calculate_aspect(hgt_data, lat, lon)
    curv = _calculate_curvature(hgt_data, lat, lon)

    return {
        "available": True,
        "source": "NASADEM 1 Arc-Second (~30m SRTM DEM)",
        "elevation_m": round(elev, 2),
        "slope_deg": round(slope, 2) if slope is not None else None,
        "aspect_deg": round(aspect, 2) if aspect is not None else None,
        "curvature": round(curv, 6) if curv is not None else None,
        "quality": "valid"
    }


def dem_data_available() -> bool:
    """Check if any NASADEM/SRTM data files exist locally."""
    for d in DEM_DIRS:
        if d.exists():
            hgt_files = list(d.glob("*.hgt")) + list(d.glob("*.zip"))
            if len(hgt_files) > 0:
                return True
    return False
