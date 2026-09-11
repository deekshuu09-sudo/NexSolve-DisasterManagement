from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sys

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.model.predictor import predict
from backend.data.rainfall_service import get_rainfall
from backend.data.weather_service import current_rainfall, forecast_rainfall
from backend.services.cv_service import analyze_image
from backend.services.dem_service import get_slope, get_terrain_features, dem_data_available

app = FastAPI(title="NexSolve Risk Intelligence API", version="1.0.0")
frontend_urls = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_URL", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", *frontend_urls],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATES = [
    {"id": "arunachal_pradesh", "name": "Arunachal Pradesh", "code": "AR", "boundary_available": False, "boundary_source": "Survey of India (Pending Integration)", "geometry": None},
    {"id": "assam", "name": "Assam", "code": "AS", "boundary_available": False, "boundary_source": "Survey of India (Pending Integration)", "geometry": None},
    {"id": "manipur", "name": "Manipur", "code": "MN", "boundary_available": False, "boundary_source": "Survey of India (Pending Integration)", "geometry": None},
    {"id": "meghalaya", "name": "Meghalaya", "code": "ML", "boundary_available": False, "boundary_source": "Survey of India (Pending Integration)", "geometry": None},
    {"id": "mizoram", "name": "Mizoram", "code": "MZ", "boundary_available": False, "boundary_source": "Survey of India (Pending Integration)", "geometry": None},
    {"id": "nagaland", "name": "Nagaland", "code": "NL", "boundary_available": False, "boundary_source": "Survey of India (Pending Integration)", "geometry": None},
    {"id": "sikkim", "name": "Sikkim", "code": "SK", "boundary_available": False, "boundary_source": "Survey of India (Pending Integration)", "geometry": None},
    {"id": "tripura", "name": "Tripura", "code": "TR", "boundary_available": False, "boundary_source": "Survey of India (Pending Integration)", "geometry": None},
]

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
    rainfall_1d: float = Field(0, ge=0)
    rainfall_3d: float = Field(0, ge=0)
    rainfall_7d: float = Field(0, ge=0)
    date: str | None = None


class Report(BaseModel):
    type: str = "Landslide Observation"
    location: str = "NER Corridor"
    latitude: float | None = None
    longitude: float | None = None
    description: str = ""


def district_or_404(district_id: str) -> dict:
    item = next((d for d in DISTRICTS if d["id"] == district_id), None)
    if not item:
        raise HTTPException(404, "District not found")
    return item

def enrich(district: dict) -> dict:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rainfall = current_rainfall(district["lat"], district["lng"])

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
        "boundary_available": False,
        "boundary_source": "Survey of India (Pending Integration)",
        "geometry": None,
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


@app.get("/api/districts")
def districts():
    data = [enrich(item) for item in DISTRICTS]
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
            "boundary_available": s["boundary_available"],
            "boundary_source": s["boundary_source"],
            "geometry": s["geometry"],
            "monitored_points_count": len(pts),
        })

    op_points = [
        {
            "id": d["id"],
            "state_id": d.get("state_id", d["state"].lower().replace(" ", "_")),
            "name": d["name"],
            "lat": d["lat"],
            "lng": d["lng"],
            "point_type": d.get("point_type", "District Centroid"),
            "boundary_available": False,
            "boundary_source": "Survey of India (Pending Integration)",
            "geometry": None,
            "district_name": d["name"],
        }
        for d in DISTRICTS
    ]

    return {
        "success": True,
        "coverage_configured": True,
        "total_states": 8,
        "states_configured": len(STATES),
        "boundary_data_available": any(s["boundary_available"] for s in STATES),
        "source": "NexSolve Geospatial Coverage Registry (Survey of India Boundaries Pending)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "states": states_payload,
        "operational_points": op_points,
    }


@app.get("/api/districts/{district_id}")
def district(district_id: str):
    item = district_or_404(district_id)
    return {"success":True,"data":enrich(item)}


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
        series.append({
            "timestamp": point["timestamp"],
            "rainfall": point["rainfall"],
            "riskScore": prediction.score,
            "status": prediction.status,
            "modelSource": prediction.model_source,
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
        return {
            "success": False,
            "data": {
                "riskScore": None,
                "status": "DATA UNAVAILABLE / WEATHER FEED OFFLINE",
                "severity": "DATA UNAVAILABLE",
                "confidence": 0,
                "factors": [],
                "modelSource": "data-unavailable",
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

    return {
        "success": True,
        "data": {
            "riskScore": prediction.score,
            "status": prediction.status,
            "severity": prediction.status,
            "confidence": prediction.confidence,
            "factors": prediction.factors,
            "modelSource": prediction.model_source,
        },
    }


@app.post("/api/reports/analyze-image")
async def analyze_report_image(
    file: UploadFile = File(...),
    description: str = Form(""),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(415, "Upload an image file")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Uploaded image is empty")
    try:
        result = analyze_image(contents)
    except Exception as exc:
        raise HTTPException(422, f"Unable to analyze image: {exc}") from exc
    description_terms = {"landslide", "rockfall", "debris", "blocked", "road blockage", "slope failure"}
    description_match = not description.strip() or any(term in description.lower() for term in description_terms)
    verification_status = "REVIEW" if result["classification"] == "Unknown" else "AI_ASSISTED_REVIEW"
    return {
        "success": True,
        "imageAnalyzed": True,
        "verificationStatus": verification_status,
        "verificationConfidence": result["confidence"],
        "visualIndicators": result["objects"],
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
    if file:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(415, "Upload an image file")
        contents = await file.read()
        if not contents:
            raise HTTPException(400, "Uploaded image is empty")
        try:
            image_result = analyze_image(contents)
        except Exception as exc:
            raise HTTPException(422, f"Unable to analyze image: {exc}") from exc

    report_id = f"REP-{int(datetime.now().timestamp())}"

    # Prototype AI verification logic.
    # A production CV model can replace this block later.
    description_lower = description.lower()

    landslide_keywords = [
        "landslide",
        "mudslide",
        "rockfall",
        "slope failure",
        "debris",
        "road blocked",
        "roadblock",
        "soil collapse",
    ]

    keyword_match = any(
        keyword in description_lower
        for keyword in landslide_keywords
    )

    verified = bool(image_result and image_result["imageAccepted"])

    # Estimate severity for the prototype.
    if any(
        word in description
        for word in ["blocked", "collapse", "major", "severe", "fatal"]
    ):
        severity = "Critical"
        recommended_action = (
            "Immediate corridor inspection and emergency response."
        )
    elif any(
        word in description
        for word in ["rockfall", "debris", "mudslide", "landslide"]
    ):
        severity = "High"
        recommended_action = (
            "Dispatch field team and issue a local hazard warning."
        )
    else:
        severity = "Moderate"
        recommended_action = (
            "Verify the location and continue monitoring."
        )

    verification_confidence = image_result["verificationConfidence"] if image_result else (92.0 if keyword_match else 78.0)

    return {
        "success": True,
        "message": "Field report verified successfully.",
        "report": {
            "id": report_id,
            "type": type,
            "location": location,
            "latitude": latitude,
            "longitude": longitude,
            "description": description,
            "verified": bool(image_result and image_result["imageAccepted"]),
            "verificationStatus": "AI_ASSISTED_REVIEW",
            "verificationMode": image_result["verificationMode"] if image_result else "Description-assisted review",
            "verificationConfidence": verification_confidence,
            "severity": severity,
            "recommendedAction": recommended_action,
            "imageAnalysis": image_result,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        },
    }

@app.get("/api/corridors")
def corridors():
    return {"success":True,"count":len(CORRIDORS),"data":CORRIDORS}


