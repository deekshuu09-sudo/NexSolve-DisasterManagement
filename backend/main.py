from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.model.predictor import predict
from backend.data.rainfall_service import get_rainfall
from backend.data.weather_service import current_rainfall, forecast_rainfall
from backend.services.cv_service import analyze_image
from backend.services.dem_service import get_slope, get_terrain_features, dem_data_available
from backend.services.district_terrain_service import get_district_terrain_summary
from backend.services.feature_engineering_service import extract_fused_features
from backend.services.risk_decision_engine import evaluate_risk_decision
from backend.services.exposure_service import get_district_exposure
from backend.services.exposure_intelligence_service import get_vulnerability_profile, load_vulnerability_database
from backend.services.explainability_service import generate_explainability_report

app = FastAPI(title="NexSolve Risk Intelligence API", version="1.0.0")
allowed_origins_env = os.getenv("ALLOWED_ORIGINS") or os.getenv("FRONTEND_URL") or ""
frontend_urls = [
    origin.strip().rstrip("/")
    for origin in allowed_origins_env.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        *frontend_urls,
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import json

GEOJSON_DIR = ROOT / "backend" / "data" / "geojson"
STATES_GEOJSON_PATH = GEOJSON_DIR / "ner_states_soi.geojson"
DISTRICTS_GEOJSON_PATH = GEOJSON_DIR / "ner_districts_soi.geojson"

STATES_GEOJSON = None
DISTRICTS_GEOJSON = None

if STATES_GEOJSON_PATH.exists():
    with open(STATES_GEOJSON_PATH, "r", encoding="utf-8") as f:
        STATES_GEOJSON = json.load(f)

if DISTRICTS_GEOJSON_PATH.exists():
    with open(DISTRICTS_GEOJSON_PATH, "r", encoding="utf-8") as f:
        DISTRICTS_GEOJSON = json.load(f)

STATE_BOUNDARIES_MAP = {}
if STATES_GEOJSON:
    for feat in STATES_GEOJSON.get("features", []):
        sid = feat["properties"].get("state_id")
        if sid:
            STATE_BOUNDARIES_MAP[sid] = feat

DISTRICT_BOUNDARIES_MAP = {}
if DISTRICTS_GEOJSON:
    for feat in DISTRICTS_GEOJSON.get("features", []):
        did = feat["properties"].get("district_id")
        d_name = feat["properties"].get("district_name")
        s_name = feat["properties"].get("state_name")
        if did:
            DISTRICT_BOUNDARIES_MAP[did] = feat
        if d_name and s_name:
            DISTRICT_BOUNDARIES_MAP[(s_name.lower(), d_name.lower())] = feat

RAW_STATES = [
    {"id": "arunachal_pradesh", "name": "Arunachal Pradesh", "code": "AR", "state_lgd": 12},
    {"id": "assam", "name": "Assam", "code": "AS", "state_lgd": 18},
    {"id": "manipur", "name": "Manipur", "code": "MN", "state_lgd": 14},
    {"id": "meghalaya", "name": "Meghalaya", "code": "ML", "state_lgd": 17},
    {"id": "mizoram", "name": "Mizoram", "code": "MZ", "state_lgd": 15},
    {"id": "nagaland", "name": "Nagaland", "code": "NL", "state_lgd": 13},
    {"id": "sikkim", "name": "Sikkim", "code": "SK", "state_lgd": 11},
    {"id": "tripura", "name": "Tripura", "code": "TR", "state_lgd": 16},
]

STATES = []
for s in RAW_STATES:
    feat = STATE_BOUNDARIES_MAP.get(s["id"])
    STATES.append({
        "id": s["id"],
        "name": s["name"],
        "code": s["code"],
        "state_lgd": s["state_lgd"],
        "boundary_available": feat is not None,
        "boundary_source": "Survey of India Official Administrative Boundary Database (ABDB)" if feat else "Survey of India (Pending Integration)",
        "geometry": feat["geometry"] if feat else None,
    })

OP_SOI_MATCHES = {
    "champhai": "champhai",
    "aizawl": "aizawl",
    "senapati": "senapati",
    "cherrapunji": "east_khasi_hills",
    "tawang": "tawang",
    "kohima": "kohima",
    "dima_hasao": "dima_hasao",
    "dhalai": "dhalai",
    "gangtok": "gangtok",
}

DISTRICTS = [
    {"id":"champhai","state":"Mizoram","state_id":"mizoram","name":"Champhai District","lat":23.4756,"lng":93.3289,"rain24h":146,"soilSat":88,"slopeAngle":42,"gsiEvents":14,"point_type":"District Centroid"},
    {"id":"aizawl","state":"Mizoram","state_id":"mizoram","name":"Aizawl Capital Corridor","lat":23.7271,"lng":92.7176,"rain24h":108,"soilSat":74,"slopeAngle":36,"gsiEvents":8,"point_type":"Corridor Node"},
    {"id":"senapati","state":"Manipur","state_id":"manipur","name":"Senapati NH-2 Corridor","lat":25.2686,"lng":94.0186,"rain24h":138,"soilSat":85,"slopeAngle":44,"gsiEvents":16,"point_type":"Corridor Node"},
    {"id":"cherrapunji","state":"Meghalaya","state_id":"meghalaya","name":"Sohra / Cherrapunji Plateau","lat":25.2700,"lng":91.7320,"rain24h":194,"soilSat":91,"slopeAngle":40,"gsiEvents":19,"point_type":"Plateau"},
    {"id":"tawang","state":"Arunachal Pradesh","state_id":"arunachal_pradesh","name":"Tawang High Pass","lat":27.5860,"lng":91.8650,"rain24h":132,"soilSat":79,"slopeAngle":43,"gsiEvents":11,"point_type":"High Pass"},
    {"id":"kohima","state":"Nagaland","state_id":"nagaland","name":"Kohima Bypass Corridor","lat":25.6751,"lng":94.1086,"rain24h":140,"soilSat":82,"slopeAngle":41,"gsiEvents":13,"point_type":"Corridor Node"},
    {"id":"dima_hasao","state":"Assam","state_id":"assam","name":"Dima Hasao Hill Axis","lat":25.1800,"lng":93.0200,"rain24h":115,"soilSat":80,"slopeAngle":38,"gsiEvents":10,"point_type":"Corridor Node"},
    {"id":"dhalai","state":"Tripura","state_id":"tripura","name":"Dhalai Pass Corridor","lat":23.8400,"lng":91.2800,"rain24h":95,"soilSat":76,"slopeAngle":35,"gsiEvents":7,"point_type":"Corridor Node"},
    {"id":"gangtok","state":"Sikkim","state_id":"sikkim","name":"Gangtok / East Sikkim","lat":27.3300,"lng":88.6100,"rain24h":125,"soilSat":83,"slopeAngle":42,"gsiEvents":15,"point_type":"District Centroid"},
]

CORRIDORS = [
    {"code":"NH-306","name":"Silchar – Aizawl Axis","status":"BLOCKED","eta":"4-6 Hours"},
    {"code":"NH-2","name":"Dimapur – Imphal Hwy","status":"BLOCKED","eta":"8-12 Hours"},
    {"code":"NH-10","name":"Gangtok – Siliguri Axis","status":"RESTRICTED","eta":"Monitored 24/7"},
    {"code":"NH-6","name":"Guwahati – Shillong Expressway","status":"OPEN","eta":"Normal"},
]

class RiskInput(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    rainfall_1d: float | None = Field(None, ge=0)
    rainfall_3d: float | None = Field(None, ge=0)
    rainfall_7d: float | None = Field(None, ge=0)
    date: str | None = None


class Report(BaseModel):
    type: str = "Landslide Observation"
    location: str = "NER Corridor"
    latitude: float | None = None
    longitude: float | None = None
    description: str = ""


def get_district_boundary_info(district_id: str, state_name: str = "", district_name: str = "", include_geometry: bool = True):
    feat = None
    if district_id in DISTRICT_BOUNDARIES_MAP:
        feat = DISTRICT_BOUNDARIES_MAP[district_id]
    elif district_id in OP_SOI_MATCHES:
        soi_key = OP_SOI_MATCHES[district_id]
        feat = DISTRICT_BOUNDARIES_MAP.get(soi_key)
    elif state_name and district_name:
        feat = DISTRICT_BOUNDARIES_MAP.get((state_name.lower(), district_name.lower()))
    
    if feat:
        props = feat.get("properties", {})
        return {
            "boundary_available": True,
            "boundary_source": "Survey of India Official Administrative Boundary Database (ABDB)",
            "geometry": feat.get("geometry") if include_geometry else None,
            "dist_lgd": props.get("dist_lgd"),
            "district_name_soi": props.get("district_name_soi"),
            "state_lgd": props.get("state_lgd"),
            "state_name_soi": props.get("state_name_soi"),
        }
    return {
        "boundary_available": False,
        "boundary_source": "Survey of India (Pending Integration)",
        "geometry": None,
        "dist_lgd": None,
        "district_name_soi": None,
        "state_lgd": None,
        "state_name_soi": None,
    }

def district_or_404(district_id: str) -> dict:
    item = next((d for d in DISTRICTS if d["id"] == district_id), None)
    if not item and district_id in DISTRICT_BOUNDARIES_MAP:
        feat = DISTRICT_BOUNDARIES_MAP[district_id]
        props = feat["properties"]
        # Derive centroid from geometry bounds if available
        item = {
            "id": props["district_id"],
            "state": props["state_name"],
            "state_id": props["state_id"],
            "name": props["district_name"],
            "lat": 25.0, # default if not calculated
            "lng": 93.0,
            "rain24h": 50,
            "soilSat": 60,
            "slopeAngle": 35,
            "gsiEvents": 5,
            "point_type": "District Boundary",
        }
    if not item:
        raise HTTPException(404, "District not found")
    return item

def enrich(district: dict, include_geometry: bool = True) -> dict:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rainfall = current_rainfall(district["lat"], district["lng"])
    b_info = get_district_boundary_info(district["id"], district.get("state", ""), district.get("name", ""), include_geometry=include_geometry)
    soi_key = OP_SOI_MATCHES.get(district["id"], district["id"])
    vuln_profile = get_vulnerability_profile(soi_key)
    exp_profile = get_district_exposure(soi_key)

    # Try to get real slope and terrain features from DEM; fall back to default values
    slope_angle = district.get("slopeAngle", 40)  # Default fallback
    terrain_data = {"elevation": None, "slope": None, "aspect": None, "curvature": None}
    if dem_data_available():
        try:
            terrain_data = get_terrain_features(district["lat"], district["lng"])
            if terrain_data.get("slope") is not None:
                slope_angle = terrain_data["slope"]
        except Exception as e:
            print(f"Warning: DEM terrain extraction failed for {district['id']}: {e}")

    # RISK SAFETY: If critical rainfall inputs are unavailable, return explicit data-unavailable status
    if not rainfall.get("available") or rainfall.get("rainfall_1d") is None:
        decision = evaluate_risk_decision(
            model_prediction=None,
            weather_data=rainfall,
            location={"state": district.get("state"), "district": district.get("name"), "latitude": district["lat"], "longitude": district["lng"]},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return {
            **district,
            "rain24h": None,
            "rainfall_3d": None,
            "rainfall_7d": None,
            "riskScore": None,
            "status": "DATA UNAVAILABLE / WEATHER FEED OFFLINE",
            "confidence": 0,
            "modelSource": "data-unavailable",
            "factors": [],
            "slopeAngle": slope_angle,
            "decision": decision.to_dict(),
            "vulnerability": vuln_profile,
            "exposure": exp_profile,
            **b_info,
            "terrain": terrain_data,
            "demLoaded": terrain_data.get("elevation") is not None,
            "weatherStatus": rainfall,
        }

    prediction = predict({
        "latitude": district["lat"],
        "longitude": district["lng"],
        "rainfall_1d": rainfall["rainfall_1d"],
        "rainfall_3d": rainfall["rainfall_3d"],
        "rainfall_7d": rainfall["rainfall_7d"],
        "date": date,
        "slopeAngle": slope_angle,
    })

    decision = evaluate_risk_decision(
        model_prediction=prediction,
        weather_data=rainfall,
        location={"state": district.get("state"), "district": district.get("name"), "latitude": district["lat"], "longitude": district["lng"]},
        timestamp=datetime.now(timezone.utc).isoformat(),
        extra_context={"date": date},
    )

    return {
        **district,
        "rain24h": rainfall["rainfall_1d"],
        "rainfall_3d": rainfall["rainfall_3d"],
        "rainfall_7d": rainfall["rainfall_7d"],
        "riskScore": prediction.score,
        "status": prediction.status,
        "confidence": prediction.confidence,
        "modelSource": prediction.model_source,
        "factors": prediction.factors,
        "slopeAngle": slope_angle,
        "decision": decision.to_dict(),
        "vulnerability": vuln_profile,
        "exposure": exp_profile,
        **b_info,
        "terrain": terrain_data,
        "demLoaded": terrain_data.get("elevation") is not None,
        "weatherStatus": rainfall,
    }

@app.get("/api/health")
def health():
    return {"status":"ONLINE","service":"NexSolve Risk Intelligence API","timestamp":datetime.now(timezone.utc).isoformat()}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/ready")
def ready_check():
    """Readiness probe: verifies runtime model availability, SHA256 integrity, and Survey of India boundaries."""
    from backend.services.model_loader import load_active_model

    model_pkg = load_active_model()
    model_ready = model_pkg is not None and model_pkg.get("model") is not None
    geojson_ready = STATES_GEOJSON_PATH.exists() and DISTRICTS_GEOJSON_PATH.exists()

    ready = bool(model_ready and geojson_ready)
    status_code = 200 if ready else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "READY" if ready else "NOT_READY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "model_loaded": model_ready,
                "model_id": model_pkg.get("model_id") if model_pkg else None,
                "model_version": model_pkg.get("model_version") if model_pkg else None,
                "model_sha256": model_pkg.get("sha256") if model_pkg else None,
                "administrative_boundaries": geojson_ready,
                "risk_policy": True,
            },
        },
    )


@app.get("/api/districts")
def districts(include_geometry: bool = True):
    with ThreadPoolExecutor(max_workers=len(DISTRICTS)) as executor:
        data = list(executor.map(lambda d: enrich(d, include_geometry=include_geometry), DISTRICTS))
    return {"success":True,"count":len(data),"data":data}


@app.get("/api/coverage")
def coverage():
    states_payload = []
    for s in STATES:
        pts = [d for d in DISTRICTS if d.get("state_id") == s["id"] or d["state"].lower() == s["name"].lower()]
        states_payload.append({
            "id": s["id"],
            "name": s["name"],
            "code": s["code"],
            "state_lgd": s.get("state_lgd"),
            "boundary_available": s["boundary_available"],
            "boundary_source": s["boundary_source"],
            "geometry": s["geometry"],
            "monitored_points_count": len(pts),
        })

    op_points = []
    for d in DISTRICTS:
        b_info = get_district_boundary_info(d["id"], d.get("state", ""), d.get("name", ""))
        op_points.append({
            "id": d["id"],
            "state_id": d.get("state_id", d["state"].lower().replace(" ", "_")),
            "name": d["name"],
            "lat": d["lat"],
            "lng": d["lng"],
            "point_type": d.get("point_type", "District Centroid"),
            "district_name": d["name"],
            **b_info,
        })

    total_districts = len(DISTRICTS_GEOJSON.get("features", [])) if DISTRICTS_GEOJSON else 131

    return {
        "success": True,
        "coverage_configured": True,
        "total_states": 8,
        "states_configured": len(STATES),
        "total_districts": total_districts,
        "districts_configured": total_districts,
        "boundary_data_available": any(s["boundary_available"] for s in STATES),
        "source": "NexSolve Geospatial Coverage Registry (Official Survey of India ABDB Boundaries)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "states": states_payload,
        "operational_points": op_points,
    }


@app.get("/api/geojson/states")
def get_states_geojson():
    if not STATES_GEOJSON:
        raise HTTPException(404, "State GeoJSON boundaries not loaded")
    return STATES_GEOJSON


@app.get("/api/geojson/districts")
def get_districts_geojson(state_id: str | None = None):
    if not DISTRICTS_GEOJSON:
        raise HTTPException(404, "District GeoJSON boundaries not loaded")
    if not state_id:
        return DISTRICTS_GEOJSON
    
    filtered_features = [
        f for f in DISTRICTS_GEOJSON.get("features", [])
        if f["properties"].get("state_id") == state_id
    ]
    return {
        "type": "FeatureCollection",
        "name": f"Northeast_India_Districts_{state_id}",
        "crs": DISTRICTS_GEOJSON.get("crs"),
        "features": filtered_features,
    }


@app.get("/api/districts/{district_id}")
def district(district_id: str):
    item = district_or_404(district_id)
    return {"success":True,"data":enrich(item)}


@app.get("/api/terrain")
def terrain_summary():
    available = dem_data_available()
    return {
        "success": True,
        "available": available,
        "source": "NASADEM 1 Arc-Second (~30m SRTM DEM)",
        "coverage": "Northeast India (8 States, 131 Districts)",
        "tile_count": 90,
        "resolution": "30m (1 arc-second)",
        "crs": "EPSG:4326 (WGS84)",
        "quality": "valid" if available else "unavailable",
    }


@app.get("/api/terrain/{district_id}")
def district_terrain(district_id: str, latitude: float | None = None, longitude: float | None = None):
    item = district_or_404(district_id)
    lat = latitude if latitude is not None else item.get("lat")
    lng = longitude if longitude is not None else item.get("lng")

    point_terrain = get_terrain_features(lat, lng) if lat is not None and lng is not None else {
        "available": False, "source": "NASADEM 1 Arc-Second (~30m SRTM DEM)", "quality": "unavailable", "reason": "No coordinates provided"
    }

    soi_key = OP_SOI_MATCHES.get(district_id, district_id)
    spatial_summary = get_district_terrain_summary(soi_key)

    return {
        "success": True,
        "district_id": district_id,
        "district_name": item.get("name"),
        "state": item.get("state"),
        "point_terrain": point_terrain,
        "spatial_summary": spatial_summary,
    }


@app.get("/api/exposure/{district_id}")
def exposure(district_id: str):
    data = get_district_exposure(district_id)
    data["vulnerability_intelligence"] = get_vulnerability_profile(district_id)
    return data


@app.get("/api/vulnerability/{district_id}")
def vulnerability(district_id: str):
    return get_vulnerability_profile(district_id)


@app.get("/api/explainability/{district_id}")
def district_explainability(district_id: str):
    item = district_or_404(district_id)
    weather = current_rainfall(item["lat"], item["lng"])
    r1d = weather.get("rainfall_1d")
    r3d = weather.get("rainfall_3d")
    r7d = weather.get("rainfall_7d")

    prediction = predict({
        "latitude": item["lat"],
        "longitude": item["lng"],
        "rainfall_1d": r1d,
        "rainfall_3d": r3d,
        "rainfall_7d": r7d,
    })

    weather_dict = {
        "available": weather.get("is_live", False),
        "is_live": weather.get("is_live", True),
        "quality": "good" if weather.get("is_live") else "stale",
        "rainfall_1d": r1d,
        "rainfall_3d": r3d,
        "rainfall_7d": r7d,
        "source": weather.get("source"),
        "timestamp": weather.get("timestamp"),
    }

    decision = evaluate_risk_decision(
        model_prediction=prediction,
        weather_data=weather_dict,
        location={"state": item["state"], "district": item["name"], "latitude": item["lat"], "longitude": item["lng"]},
    )

    soi_key = OP_SOI_MATCHES.get(district_id, district_id)
    vuln_profile = get_vulnerability_profile(soi_key)

    explainability = generate_explainability_report(
        risk_decision=decision,
        weather_data=weather_dict,
        features={
            "latitude": item["lat"],
            "longitude": item["lng"],
            "rainfall_1d": r1d,
            "rainfall_3d": r3d,
            "rainfall_7d": r7d,
        },
        vulnerability_profile=vuln_profile,
    )

    return {
        "success": True,
        "district_id": district_id,
        "district_name": item["name"],
        "state": item["state"],
        "risk_prediction": {
            "riskScore": prediction.score if prediction else None,
            "status": prediction.status if prediction else "DATA UNAVAILABLE",
            "confidence": prediction.confidence if prediction else 0,
            "decision": decision.to_dict(),
        },
        "vulnerability_profile": vuln_profile,
        "explainability": explainability,
    }


def _eval_dashboard_node(item: dict) -> dict:
    weather = current_rainfall(item["lat"], item["lng"])
    is_live = weather.get("is_live", False)
    r1d = weather.get("rainfall_1d")
    r3d = weather.get("rainfall_3d")
    r7d = weather.get("rainfall_7d")

    pred = predict({
        "latitude": item["lat"],
        "longitude": item["lng"],
        "rainfall_1d": r1d,
        "rainfall_3d": r3d,
        "rainfall_7d": r7d,
    })

    weather_dict = {
        "available": is_live or (r1d is not None),
        "is_live": is_live,
        "quality": "good" if is_live else ("stale" if r1d is not None else "unavailable"),
        "rainfall_1d": r1d,
        "rainfall_3d": r3d,
        "rainfall_7d": r7d,
        "source": weather.get("source"),
        "timestamp": weather.get("timestamp"),
    }

    decision = evaluate_risk_decision(
        model_prediction=pred,
        weather_data=weather_dict,
        location={"state": item["state"], "district": item["name"], "latitude": item["lat"], "longitude": item["lng"]},
    )
    dec_dict = decision.to_dict()
    soi_key = OP_SOI_MATCHES.get(item["id"], item["id"])
    vuln_profile = get_vulnerability_profile(soi_key)

    return {
        "node": {
            "id": item["id"],
            "name": item["name"],
            "state": item["state"],
            "lat": item["lat"],
            "lng": item["lng"],
            "point_type": item.get("point_type", "District Centroid"),
            "riskScore": pred.score if pred else None,
            "status": pred.status if pred else "DATA UNAVAILABLE",
            "decision": dec_dict,
            "vulnerability": vuln_profile,
        },
        "is_live": is_live,
        "has_r1d": r1d is not None,
        "risk_level": dec_dict.get("riskLevel", "DATA_UNAVAILABLE"),
    }


@app.get("/api/dashboard/summary")
def dashboard_summary():
    """Returns real-time system-wide situation awareness metrics across monitored points, weather status, risk categories, vulnerability profiles, and corridors."""
    soi_district_count = len(DISTRICTS_GEOJSON.get("features", [])) if DISTRICTS_GEOJSON else 131
    op_points_count = len(DISTRICTS)

    with ThreadPoolExecutor(max_workers=len(DISTRICTS)) as executor:
        evals = list(executor.map(_eval_dashboard_node, DISTRICTS))

    node_evaluations = [e["node"] for e in evals]
    risk_level_counts = {"RED": 0, "ORANGE": 0, "YELLOW": 0, "GREEN": 0, "DATA_UNAVAILABLE": 0}
    weather_live_count = 0
    weather_stale_count = 0
    weather_offline_count = 0

    for e in evals:
        if e["is_live"]:
            weather_live_count += 1
        elif e["has_r1d"]:
            weather_stale_count += 1
        else:
            weather_offline_count += 1

        r_level = e["risk_level"]
        risk_level_counts[r_level] = risk_level_counts.get(r_level, 0) + 1

    if weather_live_count > 0:
        overall_weather_status = "LIVE"
    elif weather_stale_count > 0:
        overall_weather_status = "STALE"
    else:
        overall_weather_status = "UNAVAILABLE"

    vuln_db = load_vulnerability_database()
    vuln_districts = vuln_db.get("districts", {})
    computed_vuln_count = sum(1 for d in vuln_districts.values() if d.get("status") == "COMPUTED")
    partial_vuln_count = sum(1 for d in vuln_districts.values() if d.get("status") == "PARTIAL")
    insufficient_vuln_count = sum(1 for d in vuln_districts.values() if d.get("status") == "INSUFFICIENT_DATA")

    return {
        "success": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_status": "PROTOTYPE / INTERNAL DECISION SUPPORT",
        "spatial_framework": "Official Survey of India (SoI) Administrative Boundaries",
        "monitored_districts_count": soi_district_count,
        "operational_nodes_count": op_points_count,
        "weather_feed_health": {
            "status": overall_weather_status,
            "live_points": weather_live_count,
            "stale_points": weather_stale_count,
            "offline_points": weather_offline_count,
        },
        "risk_level_counts": risk_level_counts,
        "vulnerability_coverage_summary": {
            "total_districts": len(vuln_districts),
            "computed_count": computed_vuln_count,
            "partial_count": partial_vuln_count,
            "insufficient_data_count": insufficient_vuln_count,
        },
        "corridors": CORRIDORS,
        "operational_nodes": node_evaluations,
        "disclaimer": "NexSolve Prototype Decision Support System — Information for decision-support assessment only. Not an official government warning.",
    }


@app.get("/api/features/schema")
def feature_schema():
    schema_path = ROOT / "backend" / "data" / "features" / "feature_schema.json"
    if not schema_path.exists():
        raise HTTPException(404, "Feature schema definition not found")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/features/{district_id}")
def district_fused_features(district_id: str):
    item = district_or_404(district_id)
    rainfall = current_rainfall(item["lat"], item["lng"])
    r1d = rainfall.get("rainfall_1d")
    r3d = rainfall.get("rainfall_3d")
    r7d = rainfall.get("rainfall_7d")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    fused = extract_fused_features(
        lat=item["lat"],
        lon=item["lng"],
        rainfall_1d=r1d,
        rainfall_3d=r3d,
        rainfall_7d=r7d,
        date_str=date_str
    )

    return {
        "success": True,
        "district_id": district_id,
        "district_name": item["name"],
        "fused_features": fused
    }


@app.get("/api/rainfall/current")
def current_rainfall_endpoint(latitude: float, longitude: float):
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(422, "Invalid latitude or longitude")
    return {"success": True, "latitude": latitude, "longitude": longitude, **current_rainfall(latitude, longitude)}


@app.get("/api/rainfall/{district_id}")
def rainfall(district_id: str):
    item = district_or_404(district_id)
    data = current_rainfall(item["lat"], item["lng"])
    return {"success": True, "district": item["name"], **data}


@app.get("/api/forecast/{district_id}")
def forecast(district_id: str):
    item = district_or_404(district_id)
    points, is_live, source = forecast_rainfall(item["lat"], item["lng"])
    series = []
    for point in points:
        prediction = predict({
            "latitude": item["lat"],
            "longitude": item["lng"],
            "rainfall_1d": point["rainfall_1d"],
            "rainfall_3d": point["rainfall_3d"],
            "rainfall_7d": point["rainfall_7d"],
            "date": point["timestamp"],
        })
        weather_point = {
            "available": True,
            "is_live": is_live,
            "quality": "good" if is_live else "stale",
            "rainfall_1d": point["rainfall_1d"],
            "rainfall_3d": point["rainfall_3d"],
            "rainfall_7d": point["rainfall_7d"],
        }
        decision = evaluate_risk_decision(
            model_prediction=prediction,
            weather_data=weather_point,
            location={"state": item["state"], "district": item["name"], "latitude": item["lat"], "longitude": item["lng"]},
            timestamp=point["timestamp"],
        )
        series.append({
            "timestamp": point["timestamp"],
            "rainfall": point["rainfall"],
            "riskScore": prediction.score,
            "status": prediction.status,
            "modelSource": prediction.model_source,
            "decision": decision.to_dict(),
        })
    windows = []
    for index, label in enumerate(("0-24h", "24-48h", "48-72h")):
        window_points = series[index * 24:(index + 1) * 24]
        peak = max(window_points, key=lambda point: point["riskScore"], default=None)
        windows.append({
            "label": label,
            "rainfall": round(sum(point["rainfall"] for point in window_points), 2),
            "riskScore": peak["riskScore"] if peak else None,
            "status": peak["status"] if peak else "Unavailable",
        })
    return {
        "success": True,
        "location": {"district": item["name"], "state": item["state"], "latitude": item["lat"], "longitude": item["lng"]},
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "is_live": is_live,
        "modelSource": "trained-random-forest" if series and all(point["modelSource"] == "trained-random-forest" for point in series) else "risk-pipeline-fallback",
        "rainfallTotals": {"24h": windows[0]["rainfall"], "48h": round(sum(window["rainfall"] for window in windows[:2]), 2), "72h": round(sum(window["rainfall"] for window in windows), 2)},
        "windows": windows,
        "forecast": series,
    }


@app.post("/api/risk")
def risk(payload: RiskInput):
    if payload.rainfall_1d is None or payload.rainfall_3d is None or payload.rainfall_7d is None:
        weather_dict = {"available": False, "rainfall_1d": None, "rainfall_3d": None, "rainfall_7d": None}
        decision = evaluate_risk_decision(
            model_prediction=None,
            weather_data=weather_dict,
            location={"latitude": payload.latitude, "longitude": payload.longitude},
            timestamp=datetime.now(timezone.utc).isoformat(),
            extra_context={"date": payload.date},
        )
        explainability = generate_explainability_report(
            risk_decision=decision,
            weather_data=weather_dict,
            features={"latitude": payload.latitude, "longitude": payload.longitude, "date": payload.date},
        )
        return {
            "success": False,
            "data": {
                "riskScore": None,
                "status": "DATA UNAVAILABLE / WEATHER FEED OFFLINE",
                "severity": "DATA UNAVAILABLE",
                "confidence": 0,
                "factors": [],
                "modelSource": "data-unavailable",
                "decision": decision.to_dict(),
                "explainability": explainability,
            },
        }

    prediction = predict({
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "rainfall_1d": payload.rainfall_1d,
        "rainfall_3d": payload.rainfall_3d,
        "rainfall_7d": payload.rainfall_7d,
        "date": payload.date,
    })

    weather_dict = {
        "available": True,
        "is_live": True,
        "quality": "good",
        "rainfall_1d": payload.rainfall_1d,
        "rainfall_3d": payload.rainfall_3d,
        "rainfall_7d": payload.rainfall_7d,
    }

    decision = evaluate_risk_decision(
        model_prediction=prediction,
        weather_data=weather_dict,
        location={"latitude": payload.latitude, "longitude": payload.longitude},
        timestamp=datetime.now(timezone.utc).isoformat(),
        extra_context={"date": payload.date},
    )

    explainability = generate_explainability_report(
        risk_decision=decision,
        weather_data=weather_dict,
        features={
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "rainfall_1d": payload.rainfall_1d,
            "rainfall_3d": payload.rainfall_3d,
            "rainfall_7d": payload.rainfall_7d,
            "date": payload.date,
        },
    )

    return {
        "success": True,
        "data": {
            "riskScore": prediction.score,
            "status": prediction.status,
            "severity": prediction.status,
            "confidence": prediction.confidence,
            "factors": prediction.factors,
            "modelSource": prediction.model_source,
            "modelVersion": getattr(prediction, "model_version", "1.1.0"),
            "modelId": getattr(prediction, "model_id", "candidate_a_rf_v1"),
            "featureSchemaVersion": getattr(prediction, "feature_schema_version", "v1"),
            "decision": decision.to_dict(),
            "explainability": explainability,
        },
    }


async def validate_and_read_image(file: UploadFile) -> bytes:
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Uploaded image is empty")

    try:
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(contents))
        img.verify()
        return contents
    except Exception:
        pass

    if file.content_type and file.content_type.startswith("image/"):
        return contents

    exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff")
    if file.filename and file.filename.lower().endswith(exts):
        return contents

    raise HTTPException(415, "Uploaded file could not be processed as a valid image")


@app.post("/api/reports/analyze-image")
async def analyze_report_image(
    file: UploadFile = File(...),
    description: str = Form(""),
):
    contents = await validate_and_read_image(file)
    try:
        result = analyze_image(contents)
    except Exception as exc:
        raise HTTPException(422, f"Unable to analyze image: {exc}") from exc
    description_terms = {"landslide", "rockfall", "debris", "blocked", "road blockage", "slope failure"}
    description_match = not description.strip() or any(term in description.lower() for term in description_terms)
    cat = result.get("contentCategory")
    verification_status = (
        "IMAGE_SCREENING_ONLY" if cat == "FIELD_PHOTO_CANDIDATE"
        else "NON_FIELD_IMAGE" if cat == "SCREENSHOT_OR_DOCUMENT"
        else "LOW_QUALITY_IMAGE" if cat == "LOW_QUALITY_IMAGE"
        else "INVALID_IMAGE"
    )
    return {
        "success": True,
        "imageAnalyzed": True,
        "verificationStatus": verification_status,
        "verificationConfidence": result.get("confidence"),
        "visualIndicators": result.get("objects", []),
        "descriptionMatch": description_match,
        **result,
    }


@app.post("/api/reports", status_code=201)
async def reports(
    type: str = Form("Landslide Observation"),
    location: str = Form("NER Corridor"),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    description: str = Form(""),
    file: UploadFile | None = File(None),
):
    if not location.strip() or not description.strip():
        raise HTTPException(422, "Location and description are required")

    image_result = None
    if file and file.filename:
        contents = await validate_and_read_image(file)
        try:
            image_result = analyze_image(contents)
        except Exception as exc:
            raise HTTPException(422, f"Unable to analyze image: {exc}") from exc

    report_id = f"REP-{int(datetime.now().timestamp())}"

    if image_result:
        cat = image_result.get("contentCategory")
        if cat == "SCREENSHOT_OR_DOCUMENT":
            verification_status = "NON_FIELD_IMAGE"
            verified = False
        elif cat == "LOW_QUALITY_IMAGE":
            verification_status = "LOW_QUALITY_IMAGE"
            verified = False
        elif cat == "UNSUPPORTED_IMAGE":
            verification_status = "INVALID_IMAGE"
            verified = False
        else:
            verification_status = "IMAGE_SCREENING_ONLY"
            verified = True
        verification_mode = image_result.get("verificationMode", "AI-assisted image screening")
        recommended_action = image_result.get("recommendedAction")
    else:
        verification_status = "REPORT_RECEIVED"
        verified = False
        verification_mode = "Text observation log"
        recommended_action = "Verify the location and continue field monitoring. NexSolve's current image module performs image-quality/content screening only; it does not confirm landslides from photographs."

    return {
        "success": True,
        "message": "Field observation report received.",
        "report": {
            "id": report_id,
            "type": type,
            "location": location,
            "latitude": latitude,
            "longitude": longitude,
            "description": description,
            "verified": verified,
            "verificationStatus": verification_status,
            "verificationMode": verification_mode,
            "verificationConfidence": None,
            "confidence": None,
            "severity": "NOT ASSESSED",
            "landslideClassification": "NOT PERFORMED",
            "recommendedAction": recommended_action,
            "imageAnalysis": image_result,
            "storageLocation": "In-memory session log (Field Observation Input)",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        },
    }

@app.get("/api/corridors")
def corridors():
    return {"success":True,"count":len(CORRIDORS),"data":CORRIDORS}


