"""DEM (Digital Elevation Model) service for terrain feature extraction.

Supports loading NASADEM HGT files and extracting elevation, slope, aspect, and curvature.
Falls back gracefully if DEM files are not available.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Optional
import math
import numpy as np

# NASADEM data directory
DEM_DIR = Path(__file__).resolve().parents[1] / "data" / "DEM"

# NASADEM HGT format: 1201 x 1201 int16 samples at 1 arc-second resolution
HGT_SIZE = 1201
HGT_BYTES = HGT_SIZE * HGT_SIZE * 2  # Each sample is int16 (2 bytes)
ARC_SECOND_TO_DEGREE = 1.0 / 3600.0


def _get_hgt_filename(lat: float, lon: float) -> str:
    """Get NASADEM HGT filename for a given latitude/longitude.
    
    NASADEM files are named: NASADEM_HGT_nXXeYYY.hgt
    where XX is latitude (padded to 2 digits) and YYY is longitude (padded to 3 digits)
    
    Example: NASADEM_HGT_n23e087.hgt for coordinates around 23°N, 87°E
    """
    lat_int = int(math.floor(lat))
    lon_int = int(math.floor(lon))
    
    lat_str = f"n{abs(lat_int):02d}" if lat_int >= 0 else f"s{abs(lat_int):02d}"
    lon_str = f"e{abs(lon_int):03d}" if lon_int >= 0 else f"w{abs(lon_int):03d}"
    
    return f"NASADEM_HGT_{lat_str}{lon_str}.hgt"


def _load_hgt_file(lat: float, lon: float) -> Optional[np.ndarray]:
    """Load a NASADEM HGT file and return as numpy array.
    
    Supports .hgt files as well as zipped NASADEM archives (.zip).
    Returns None if file not found.
    """
    filename = _get_hgt_filename(lat, lon)
    candidate_dirs = [
        DEM_DIR,
        Path(__file__).resolve().parents[1] / "data" / "dem",
        Path(__file__).resolve().parents[2] / "data" / "dem",
        Path(__file__).resolve().parents[2] / "data" / "DEM",
    ]
    
    for d in candidate_dirs:
        if not d.exists():
            continue
        
        # 1. Direct .hgt file
        filepath = d / filename
        if filepath.exists():
            try:
                with open(filepath, 'rb') as f:
                    data = f.read(HGT_BYTES)
                elevations = np.frombuffer(data, dtype='>i2').reshape((HGT_SIZE, HGT_SIZE))
                return elevations
            except Exception as e:
                print(f"Error loading HGT file {filepath}: {e}")
        
        # 2. Check for zip files containing .hgt
        import zipfile
        zip_candidates = list(d.glob(f"*{filename.replace('.hgt', '')}*.zip")) + list(d.glob("*.zip"))
        for zpath in zip_candidates:
            try:
                with zipfile.ZipFile(zpath, 'r') as zf:
                    for zmember in zf.namelist():
                        if zmember.endswith('.hgt') and (filename in zmember or zmember.lower() == filename.lower()):
                            data = zf.read(zmember)[:HGT_BYTES]
                            if len(data) == HGT_BYTES:
                                elevations = np.frombuffer(data, dtype='>i2').reshape((HGT_SIZE, HGT_SIZE))
                                return elevations
            except Exception as e:
                pass

    return None



def _get_elevation_from_hgt(
    hgt_data: np.ndarray,
    lat: float,
    lon: float
) -> Optional[float]:
    """Extract elevation from HGT array at specific lat/lon.
    
    HGT files contain 1201x1201 samples covering 1 degree x 1 degree.
    Samples are at 1 arc-second resolution.
    
    The array is stored with:
    - Row 0: northernmost latitude
    - Row 1200: southernmost latitude
    - Col 0: westernmost longitude
    - Col 1200: easternmost longitude
    """
    lat_int = int(math.floor(lat))
    lon_int = int(math.floor(lon))
    
    # Offset within the tile (0-1 degree range)
    lat_offset = lat - lat_int
    lon_offset = lon - lon_int
    
    # Convert to pixel indices (1201 samples covers 1 degree + overlap)
    # At 1 arc-second resolution: 1 degree = 3600 arc-seconds
    row = int((1.0 - lat_offset) * 3600)
    col = int(lon_offset * 3600)
    
    # Clamp to valid range
    row = max(0, min(HGT_SIZE - 1, row))
    col = max(0, min(HGT_SIZE - 1, col))
    
    elevation = float(hgt_data[row, col])
    
    # NASADEM uses -32768 for void/water pixels, ignore those
    if elevation == -32768:
        return None
    
    return elevation


def _calculate_slope(
    hgt_data: np.ndarray,
    lat: float,
    lon: float,
    resolution_m: float = 30.0
) -> Optional[float]:
    """Calculate slope in degrees at a location using local gradient.
    
    Uses 3x3 Sobel operator for gradient estimation.
    
    Args:
        hgt_data: NASADEM elevation array
        lat: Latitude
        lon: Longitude
        resolution_m: Ground resolution in meters (NASADEM is ~30m at equator)
    
    Returns:
        Slope in degrees (0-90), or None if unable to calculate
    """
    lat_int = int(math.floor(lat))
    lon_int = int(math.floor(lon))
    
    lat_offset = lat - lat_int
    lon_offset = lon - lon_int
    
    row = int((1.0 - lat_offset) * 3600)
    col = int(lon_offset * 3600)
    
    # Clamp with buffer for Sobel operator
    row = max(1, min(HGT_SIZE - 2, row))
    col = max(1, min(HGT_SIZE - 2, col))
    
    # Get 3x3 neighborhood
    neighborhood = hgt_data[row - 1 : row + 2, col - 1 : col + 2]
    
    # Check for void pixels
    if np.any(neighborhood == -32768):
        return None
    
    # Sobel operators for x and y gradients
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
    
    grad_x = np.sum(neighborhood * sobel_x)
    grad_y = np.sum(neighborhood * sobel_y)
    
    # Gradient magnitude
    grad_magnitude = math.sqrt(grad_x ** 2 + grad_y ** 2) / 8.0  # Sobel normalization
    
    # Convert to slope angle (rise/run in meters)
    # grad_magnitude is in elevation units per pixel
    slope_radians = math.atan(grad_magnitude / resolution_m)
    slope_degrees = math.degrees(slope_radians)
    
    return max(0, min(90, slope_degrees))


def _calculate_aspect(
    hgt_data: np.ndarray,
    lat: float,
    lon: float
) -> Optional[float]:
    """Calculate aspect (direction of steepest slope) in degrees (0-360).
    
    0° = North, 90° = East, 180° = South, 270° = West
    Returns None if unable to calculate.
    """
    lat_int = int(math.floor(lat))
    lon_int = int(math.floor(lon))
    
    lat_offset = lat - lat_int
    lon_offset = lon - lon_int
    
    row = int((1.0 - lat_offset) * 3600)
    col = int(lon_offset * 3600)
    
    row = max(1, min(HGT_SIZE - 2, row))
    col = max(1, min(HGT_SIZE - 2, col))
    
    neighborhood = hgt_data[row - 1 : row + 2, col - 1 : col + 2]
    
    if np.any(neighborhood == -32768):
        return None
    
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
    
    grad_x = np.sum(neighborhood * sobel_x)
    grad_y = np.sum(neighborhood * sobel_y)
    
    # Aspect: atan2(grad_x, -grad_y)
    # Negative grad_y because row increases downward
    aspect_radians = math.atan2(grad_x, -grad_y)
    aspect_degrees = math.degrees(aspect_radians)
    
    # Convert to 0-360 range where 0 = North
    aspect_degrees = (90 - aspect_degrees) % 360
    
    return aspect_degrees


def _calculate_curvature(
    hgt_data: np.ndarray,
    lat: float,
    lon: float,
    resolution_m: float = 30.0
) -> Optional[float]:
    """Calculate laplacian profile curvature (second derivative) of elevation.
    
    Positive curvature indicates convex surface (crest/ridge),
    negative indicates concave surface (gully/valley), near 0 indicates flat/uniform slope.
    """
    lat_int = int(math.floor(lat))
    lon_int = int(math.floor(lon))
    
    lat_offset = lat - lat_int
    lon_offset = lon - lon_int
    
    row = int((1.0 - lat_offset) * 3600)
    col = int(lon_offset * 3600)
    
    row = max(1, min(HGT_SIZE - 2, row))
    col = max(1, min(HGT_SIZE - 2, col))
    
    neighborhood = hgt_data[row - 1 : row + 2, col - 1 : col + 2]
    
    if np.any(neighborhood == -32768):
        return None
    
    # 5-point discrete Laplacian operator for 2D second derivative
    # [ 0,  1, 0]
    # [ 1, -4, 1]
    # [ 0,  1, 0]
    center = float(neighborhood[1, 1])
    neighbors_sum = (
        float(neighborhood[0, 1]) +
        float(neighborhood[2, 1]) +
        float(neighborhood[1, 0]) +
        float(neighborhood[1, 2])
    )
    
    curvature = (neighbors_sum - 4.0 * center) / (resolution_m ** 2)
    return float(curvature)


def get_elevation(lat: float, lon: float) -> Optional[float]:
    """Get elevation in meters at given lat/lon.
    
    Returns None if DEM data not available.
    """
    hgt_data = _load_hgt_file(lat, lon)
    if hgt_data is None:
        return None
    
    return _get_elevation_from_hgt(hgt_data, lat, lon)


def get_slope(lat: float, lon: float) -> Optional[float]:
    """Get slope in degrees at given lat/lon.
    
    Range: 0-90 degrees
    Returns None if DEM data not available.
    """
    hgt_data = _load_hgt_file(lat, lon)
    if hgt_data is None:
        return None
    
    return _calculate_slope(hgt_data, lat, lon)


def get_aspect(lat: float, lon: float) -> Optional[float]:
    """Get aspect (direction of steepest slope) in degrees at given lat/lon.
    
    Range: 0-360 degrees (0=North, 90=East, 180=South, 270=West)
    Returns None if DEM data not available.
    """
    hgt_data = _load_hgt_file(lat, lon)
    if hgt_data is None:
        return None
    
    return _calculate_aspect(hgt_data, lat, lon)


def get_curvature(lat: float, lon: float) -> Optional[float]:
    """Get profile curvature at given lat/lon.
    
    Returns None if DEM data not available.
    """
    hgt_data = _load_hgt_file(lat, lon)
    if hgt_data is None:
        return None
    
    return _calculate_curvature(hgt_data, lat, lon)


def get_terrain_features(lat: float, lon: float) -> dict[str, Optional[float]]:
    """Get all available terrain features at given lat/lon.
    
    Returns dict with keys: elevation, slope, aspect, curvature
    Each value is None if not available.
    """
    hgt_data = _load_hgt_file(lat, lon)
    
    if hgt_data is None:
        return {
            "elevation": None,
            "slope": None,
            "aspect": None,
            "curvature": None,
        }
    
    return {
        "elevation": _get_elevation_from_hgt(hgt_data, lat, lon),
        "slope": _calculate_slope(hgt_data, lat, lon),
        "aspect": _calculate_aspect(hgt_data, lat, lon),
        "curvature": _calculate_curvature(hgt_data, lat, lon),
    }


def dem_data_available() -> bool:
    """Check if any NASADEM data is available locally."""
    for d in [DEM_DIR, Path(__file__).resolve().parents[1] / "data" / "dem", Path(__file__).resolve().parents[2] / "data" / "dem", Path(__file__).resolve().parents[2] / "data" / "DEM"]:
        if d.exists():
            hgt_files = list(d.glob("*.hgt")) + list(d.glob("*.zip"))
            if len(hgt_files) > 0:
                return True
    return False

