#!/usr/bin/env python3
"""
Convert official Survey of India (ABDB) Shapefiles to WGS84 EPSG:4326 GeoJSON
for 8 Northeast India States and 131 Northeast Districts.
"""

import json
from pathlib import Path
import shapefile
from pyproj import CRS, Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform

# Define paths
BASE_DIR = Path(__file__).resolve().parents[2]
SOI_DIR = BASE_DIR / "temp_soi_validation" / "State_District_Subdistrict_PAN INDIA"
STATE_SHP = SOI_DIR / "State Boundary" / "State Boundary.shp"
STATE_PRJ = SOI_DIR / "State Boundary" / "State Boundary.prj"
DIST_SHP = SOI_DIR / "District_Subdistrict_PAN INDIA" / "District Boundary.shp"
DIST_PRJ = SOI_DIR / "District_Subdistrict_PAN INDIA" / "District Boundary.prj"

OUTPUT_DIR = BASE_DIR / "backend" / "data" / "geojson"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATE_GEOJSON_PATH = OUTPUT_DIR / "ner_states_soi.geojson"
DIST_GEOJSON_PATH = OUTPUT_DIR / "ner_districts_soi.geojson"

# NE States definition & LGD mapping
NE_STATE_LGD_MAP = {
    "SIKKIM": (11, "sikkim", "Sikkim"),
    "ARUNACHAL PRADESH": (12, "arunachal_pradesh", "Arunachal Pradesh"),
    "NAGALAND": (13, "nagaland", "Nagaland"),
    "MANIPUR": (14, "manipur", "Manipur"),
    "MIZORAM": (15, "mizoram", "Mizoram"),
    "TRIPURA": (16, "tripura", "Tripura"),
    "MEGHALAYA": (17, "meghalaya", "Meghalaya"),
    "ASSAM": (18, "assam", "Assam"),
}

# Transformer setup
with open(STATE_PRJ, "r") as f:
    state_crs_wkt = f.read()

crs_lcc = CRS.from_wkt(state_crs_wkt)
crs_4326 = CRS.from_epsg(4326)
transformer = Transformer.from_crs(crs_lcc, crs_4326, always_xy=True)

def project_to_2d(x, y, z=None):
    lon, lat = transformer.transform(x, y)
    return (lon, lat)

def clean_diacritics(text: str) -> str:
    if not text:
        return ""
    # Replace '>' with 'A' as used in official DBF diacritic encoding
    cleaned = text.replace(">", "A")
    # Titlecase for clean display, handling special cases
    words = cleaned.split()
    title_words = []
    for w in words:
        if w.upper() in ["AND", "OF", "THE", "UT"]:
            title_words.append(w.lower())
        else:
            title_words.append(w.capitalize())
    res = " ".join(title_words)
    if res and res[0].islower():
        res = res[0].upper() + res[1:]
    return res

def convert_states():
    print(f"Reading state shapefile: {STATE_SHP}")
    sf = shapefile.Reader(str(STATE_SHP))
    features = []

    for sr in sf.shapeRecords():
        rec = sr.record.as_dict()
        state_soi = rec.get("STATE", "").strip()
        if state_soi in NE_STATE_LGD_MAP:
            lgd_code, state_id, state_name = NE_STATE_LGD_MAP[state_soi]
            geom = shape(sr.__geo_interface__)
            geom_4326 = transform(project_to_2d, geom)
            
            feat = {
                "type": "Feature",
                "id": state_id,
                "properties": {
                    "state_id": state_id,
                    "state_name": state_name,
                    "state_name_soi": state_soi,
                    "state_lgd": lgd_code,
                    "OBJECTID": rec.get("OBJECTID"),
                    "Shape_Leng": rec.get("Shape_Leng"),
                    "Shape_Area": rec.get("Shape_Area"),
                    "Country": rec.get("Country", "India"),
                    "boundary_source": "Survey of India Official Administrative Boundary Database (ABDB)"
                },
                "geometry": mapping(geom_4326)
            }
            features.append(feat)

    features.sort(key=lambda f: f["properties"]["state_name"])
    fc = {
        "type": "FeatureCollection",
        "name": "Northeast_India_States_Survey_of_India",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": features
    }

    with open(STATE_GEOJSON_PATH, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"Successfully created {STATE_GEOJSON_PATH} with {len(features)} state polygons.")

def convert_districts():
    print(f"Reading district shapefile: {DIST_SHP}")
    sf = shapefile.Reader(str(DIST_SHP))
    features = []

    ne_state_soi_names = set(NE_STATE_LGD_MAP.keys())

    for sr in sf.shapeRecords():
        rec = sr.record.as_dict()
        state_ut = rec.get("STATE_UT", "").strip()
        state_lgd = rec.get("STATE_LGD")

        if state_ut in ne_state_soi_names or state_lgd in [v[0] for v in NE_STATE_LGD_MAP.values()]:
            if state_ut in NE_STATE_LGD_MAP:
                lgd_code, state_id, state_name = NE_STATE_LGD_MAP[state_ut]
            else:
                match = next((v for v in NE_STATE_LGD_MAP.values() if v[0] == state_lgd), None)
                if match:
                    lgd_code, state_id, state_name = match
                else:
                    continue

            dist_soi = rec.get("DISTRICT", "").strip()
            dist_lgd = rec.get("DIST_LGD")
            dist_name = clean_diacritics(dist_soi)
            
            dist_id_slug = dist_name.lower().replace(" ", "_").replace("-", "_").replace(">", "a")
            
            geom = shape(sr.__geo_interface__)
            geom_4326 = transform(project_to_2d, geom)

            feat = {
                "type": "Feature",
                "id": dist_id_slug,
                "properties": {
                    "district_id": dist_id_slug,
                    "district_name": dist_name,
                    "district_name_soi": dist_soi,
                    "dist_lgd": dist_lgd,
                    "state_name": state_name,
                    "state_name_soi": state_ut,
                    "state_lgd": lgd_code,
                    "state_id": state_id,
                    "OBJECTID": rec.get("OBJECTID"),
                    "REMARKS": rec.get("REMARKS"),
                    "Shape_Leng": rec.get("Shape_Leng"),
                    "Shape_Area": rec.get("Shape_Area"),
                    "boundary_source": "Survey of India Official Administrative Boundary Database (ABDB)"
                },
                "geometry": mapping(geom_4326)
            }
            features.append(feat)

    features.sort(key=lambda f: (f["properties"]["state_name"], f["properties"]["district_name"]))
    fc = {
        "type": "FeatureCollection",
        "name": "Northeast_India_Districts_Survey_of_India",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": features
    }

    with open(DIST_GEOJSON_PATH, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"Successfully created {DIST_GEOJSON_PATH} with {len(features)} district polygons.")

if __name__ == "__main__":
    convert_states()
    convert_districts()
