"""Canonical Feature Engineering Service for NexSolve (P4).

Fuses:
1. Official Survey of India Administrative Boundaries
2. NASADEM / SRTM 30m Terrain Features
3. IMD Rainfall & Weather Observations
4. Geological Survey of India (GSI) Landslide Inventory Context
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from shapely.geometry import shape, Point

BASE_DIR = Path(__file__).resolve().parents[2]

STATE_GEOJSON_PATH = BASE_DIR / "backend" / "data" / "geojson" / "ner_states_soi.geojson"
DISTRICT_GEOJSON_PATH = BASE_DIR / "backend" / "data" / "geojson" / "ner_districts_soi.geojson"
INVENTORY_CSV_PATH = BASE_DIR / "backend" / "data" / "landslides" / "ner_landslides.csv"

from backend.services.dem_service import get_terrain_features
from backend.services.district_terrain_service import get_district_terrain_summary

# Global spatial index caches
STATE_SHAPES: List[Dict[str, Any]] = []
DISTRICT_SHAPES: List[Dict[str, Any]] = []
INVENTORY_EVENTS: List[Dict[str, Any]] = []
INVENTORY_TREE = None
INVENTORY_DF = None
import datetime
import re

MONTH_MAP = {
    'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
    'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
    'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9, 'october': 10, 'oct': 10,
    'november': 11, 'nov': 11, 'december': 12, 'dec': 12
}


def parse_inventory_temporal_info(hist_val: str, slide_no_val: str) -> Tuple[str, Optional[datetime.date], Optional[int], Optional[int]]:
    """Parse multi-tier temporal information from inventory history and slide_no fields."""
    hist = hist_val.strip() if hist_val else ""
    sn = slide_no_val.strip() if slide_no_val else ""

    # Tier 1: EXACT_DATE e.g. '28 May 2024', '17 May 2016', '02 April 2010', '28th September 2024'
    m_exact = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(20\d\d|19\d\d)', hist)
    if m_exact:
        d_str, m_str, y_str = m_exact.groups()
        m_lower = m_str.lower()
        if m_lower in MONTH_MAP:
            try:
                dt = datetime.date(int(y_str), MONTH_MAP[m_lower], int(d_str))
                return "EXACT_DATE", dt, int(y_str), MONTH_MAP[m_lower]
            except Exception:
                pass

    # Tier 2: MONTH_YEAR e.g. 'July 2024', 'June 2025', 'May 2014'
    m_my = re.search(r'([A-Za-z]+)\s+(20\d\d|19\d\d)', hist)
    if m_my:
        m_str, y_str = m_my.groups()
        m_lower = m_str.lower()
        if m_lower in MONTH_MAP:
            return "MONTH_YEAR", None, int(y_str), MONTH_MAP[m_lower]

    # Tier 3: YEAR_ONLY e.g. '2016' or slide_no 'ASM/HKN/83D07/2020/2'
    m_yr_sn = re.search(r'/(20\d\d|19\d\d)/', sn)
    m_yr_hist = re.search(r'\b(20\d\d|19\d\d)\b', hist)

    if m_yr_sn:
        return "YEAR_ONLY", None, int(m_yr_sn.group(1)), None
    elif m_yr_hist:
        return "YEAR_ONLY", None, int(m_yr_hist.group(1)), None

    # Tier 4: NO_TEMPORAL_INFO
    return "NO_TEMPORAL_INFO", None, None, None


def _init_spatial_indexes():
    global STATE_SHAPES, DISTRICT_SHAPES, INVENTORY_EVENTS, INVENTORY_DF

    if not STATE_SHAPES and STATE_GEOJSON_PATH.exists():
        with open(STATE_GEOJSON_PATH, "r", encoding="utf-8") as f:
            s_data = json.load(f)
        STATE_SHAPES = [
            {
                "state_id": feat["properties"]["state_id"],
                "state_name": feat["properties"]["state_name"],
                "state_lgd": feat["properties"]["state_lgd"],
                "shape": shape(feat["geometry"])
            }
            for feat in s_data.get("features", [])
        ]

    if not DISTRICT_SHAPES and DISTRICT_GEOJSON_PATH.exists():
        with open(DISTRICT_GEOJSON_PATH, "r", encoding="utf-8") as f:
            d_data = json.load(f)
        DISTRICT_SHAPES = [
            {
                "district_id": feat["properties"]["district_id"],
                "district_name": feat["properties"]["district_name"],
                "state_name": feat["properties"]["state_name"],
                "state_id": feat["properties"]["state_id"],
                "dist_lgd": feat["properties"]["dist_lgd"],
                "state_lgd": feat["properties"]["state_lgd"],
                "shape_area": feat["properties"].get("Shape_Area", 0.1),
                "shape": shape(feat["geometry"])
            }
            for feat in d_data.get("features", [])
        ]

    if not INVENTORY_EVENTS and INVENTORY_CSV_PATH.exists():
        df = pd.read_csv(INVENTORY_CSV_PATH)
        INVENTORY_DF = df
        INVENTORY_EVENTS = []
        for idx, row in df.iterrows():
            lat = row.get("latitude")
            lon = row.get("longitude")
            slide_no = str(row.get("slide_no")) if pd.notna(row.get("slide_no")) else ""
            hist_val = str(row.get("history")) if pd.notna(row.get("history")) else ""

            tier, exact_dt, yr, mo = parse_inventory_temporal_info(hist_val, slide_no)

            if pd.notna(lat) and pd.notna(lon):
                INVENTORY_EVENTS.append({
                    "serial_no": row.get("serial_no"),
                    "slide_no": slide_no,
                    "lat": float(lat),
                    "lon": float(lon),
                    "state": row.get("state"),
                    "district": row.get("district"),
                    "temporal_tier": tier,
                    "exact_date": exact_dt,
                    "year": yr,
                    "month": mo
                })


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Haversine distance in kilometers between two lat/lon points."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_spatial_boundary_info(lat: float, lon: float) -> Dict[str, Any]:
    """Perform point-in-polygon spatial join against official Survey of India boundaries."""
    _init_spatial_indexes()
    pt = Point(lon, lat)

    matched_state = next((s for s in STATE_SHAPES if s["shape"].contains(pt)), None)
    matched_dist = next((d for d in DISTRICT_SHAPES if d["shape"].contains(pt)), None)

    if matched_dist:
        return {
            "inside_ner": True,
            "state_id": matched_dist["state_id"],
            "state_name": matched_dist["state_name"],
            "state_lgd": matched_dist["state_lgd"],
            "district_id": matched_dist["district_id"],
            "district_name": matched_dist["district_name"],
            "dist_lgd": matched_dist["dist_lgd"],
            "boundary_source": "Survey of India Official Administrative Boundary Database (ABDB)"
        }

    if matched_state:
        return {
            "inside_ner": True,
            "state_id": matched_state["state_id"],
            "state_name": matched_state["state_name"],
            "state_lgd": matched_state["state_lgd"],
            "district_id": None,
            "district_name": None,
            "dist_lgd": None,
            "boundary_source": "Survey of India Official Administrative Boundary Database (ABDB)"
        }

    return {
        "inside_ner": False,
        "state_id": None,
        "state_name": None,
        "state_lgd": None,
        "district_id": None,
        "district_name": None,
        "dist_lgd": None,
        "boundary_source": "Survey of India Official Administrative Boundary Database (ABDB)"
    }


def get_inventory_context(
    lat: float,
    lon: float,
    district_id: Optional[str] = None,
    prediction_date: Optional[str] = None,
    exclude_slide_no: Optional[str] = None,
    is_positive: bool = False
) -> Dict[str, Any]:
    """Extract spatial landslide inventory metrics, strictly enforcing multi-tier temporal cutoffs and target exclusion."""
    _init_spatial_indexes()

    pred_dt = None
    pred_year = None
    pred_month = None

    if prediction_date:
        try:
            dt_obj = pd.to_datetime(prediction_date)
            pred_dt = dt_obj.date()
            pred_year = dt_obj.year
            pred_month = dt_obj.month
        except Exception:
            pass

    filtered_events = []
    for e in INVENTORY_EVENTS:
        tier = e.get("temporal_tier", "NO_TEMPORAL_INFO")

        # Rule D: NO_TEMPORAL_INFO events MUST NOT contribute to time-dependent inventory metrics
        if tier == "NO_TEMPORAL_INFO":
            continue

        if prediction_date and pred_year is not None:
            # Rule A: EXACT_DATE -> event_date <= prediction_date
            if tier == "EXACT_DATE":
                if e.get("exact_date") is None or e["exact_date"] > pred_dt:
                    continue

            # Rule B: MONTH_YEAR -> conservative month-level cutoff (later month in same year cannot contaminate earlier prediction month)
            elif tier == "MONTH_YEAR":
                ey, em = e.get("year"), e.get("month")
                if ey is None or ey > pred_year:
                    continue
                if ey == pred_year and em is not None and em > pred_month:
                    continue

            # Rule C: YEAR_ONLY -> event_year <= prediction_year
            elif tier == "YEAR_ONLY":
                ey = e.get("year")
                if ey is None or ey > pred_year:
                    continue

        # Target event exclusion by slide_no
        if exclude_slide_no and e.get("slide_no") == exclude_slide_no:
            continue

        # Target event exclusion by co-located coordinates for positive sample
        if is_positive and pred_year is not None:
            d_km = haversine_distance_km(lat, lon, e["lat"], e["lon"])
            if d_km < 0.05 and (e.get("year") == pred_year or e.get("year") is None):
                continue

        filtered_events.append(e)

    min_dist_km = None
    if filtered_events:
        distances = [haversine_distance_km(lat, lon, e["lat"], e["lon"]) for e in filtered_events]
        min_dist_km = round(min(distances), 3)

    dist_event_count = 0
    dist_density = None
    if district_id:
        d_match = next((d for d in DISTRICT_SHAPES if d["district_id"] == district_id), None)
        if d_match:
            d_shape = d_match["shape"]
            dist_event_count = sum(1 for e in filtered_events if d_shape.contains(Point(e["lon"], e["lat"])))
            sa = d_match.get("shape_area", 0.1)
            area_sqkm = sa / 1_000_000.0 if sa > 1000.0 else sa * 11200.0
            dist_density = round(dist_event_count / area_sqkm, 6) if area_sqkm > 0 else 0.0

    return {
        "total_ner_inventory_events": len(INVENTORY_EVENTS),
        "eligible_inventory_events": len(filtered_events),
        "district_event_count": dist_event_count,
        "event_density_per_sqkm": dist_density,
        "distance_to_nearest_event_km": min_dist_km,
        "prediction_year": pred_year,
        "prediction_date": str(pred_dt) if pred_dt else None,
        "target_excluded": is_positive or exclude_slide_no is not None
    }


def extract_fused_features(
    lat: float,
    lon: float,
    rainfall_1d: Optional[float] = None,
    rainfall_3d: Optional[float] = None,
    rainfall_7d: Optional[float] = None,
    date_str: Optional[str] = None,
    exclude_slide_no: Optional[str] = None,
    is_positive: bool = False
) -> Dict[str, Any]:
    """Build unified feature-fusion dictionary combining admin boundary, terrain, weather, and inventory layers."""
    boundary_info = get_spatial_boundary_info(lat, lon)
    district_id = boundary_info.get("district_id")

    # Terrain features
    point_terrain = get_terrain_features(lat, lon)
    spatial_terrain_summary = get_district_terrain_summary(district_id) if district_id else {}

    # Inventory context (temporal cutoff & target exclusion enforced)
    inventory_context = get_inventory_context(
        lat=lat,
        lon=lon,
        district_id=district_id,
        prediction_date=date_str,
        exclude_slide_no=exclude_slide_no,
        is_positive=is_positive
    )


    # Seasonal cyclical features
    month_sin = None
    month_cos = None
    if date_str:
        try:
            m = pd.to_datetime(date_str).month
            month_sin = round(float(math.sin(2 * math.pi * m / 12)), 4)
            month_cos = round(float(math.cos(2 * math.pi * m / 12)), 4)
        except Exception:
            pass

    return {
        "location": {
            "latitude": lat,
            "longitude": lon,
            "date": date_str,
            **boundary_info
        },
        "static_terrain": {
            "point_terrain": point_terrain,
            "district_spatial_summary": spatial_terrain_summary
        },
        "dynamic_weather": {
            "rainfall_1d": rainfall_1d,
            "rainfall_3d": rainfall_3d,
            "rainfall_7d": rainfall_7d,
            "month_sin": month_sin,
            "month_cos": month_cos,
            "status": "VALID_OBSERVATION" if rainfall_1d is not None else "UNAVAILABLE"
        },
        "landslide_inventory": inventory_context,
        "provenance": {
            "boundary_source": "Survey of India Official ABDB (ner_districts_soi.geojson)",
            "terrain_source": "USGS / AWS Open Data Elevation Archive (NASADEM / SRTM1 30m)",
            "weather_source": "IMD High-Resolution Gridded Daily Rainfall Feed",
            "inventory_source": "Geological Survey of India (GSI) 10,492 Landslide Inventory"
        }
    }
