from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import urllib.parse
import urllib.request

import numpy as np
import xarray as xr

from backend.data.rainfall_service import RAIN_DIR

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 8


def _open_meteo(lat: float, lon: float) -> dict:
    query = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": "precipitation",
        "hourly": "precipitation",
        "past_days": 7,
        "forecast_days": 4,
        "timezone": "UTC",
    })
    request = urllib.request.Request(
        f"{OPEN_METEO_URL}?{query}",
        headers={"User-Agent": "NexSolve-Risk-Intelligence/1.0"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.load(response)


def _hourly_points(data: dict) -> list[tuple[datetime, float]]:
    hourly = data.get("hourly", {})
    return [
        (datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc), float(rainfall or 0))
        for timestamp, rainfall in zip(hourly.get("time", []), hourly.get("precipitation", []))
    ]


def _accumulation(points: list[tuple[datetime, float]], end: datetime, hours: int) -> float:
    start = end - timedelta(hours=hours - 1)
    return round(sum(value for timestamp, value in points if start <= timestamp <= end), 2)


def current_rainfall(lat: float, lon: float) -> dict:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    try:
        data = _open_meteo(lat, lon)
        points = _hourly_points(data)
        past = [(timestamp, value) for timestamp, value in points if timestamp <= now]
        if not past:
            raise ValueError("No current weather observations returned")
        current = data.get("current", {})
        current_value = current.get("precipitation")
        r1d = _accumulation(past, now, 24)
        r3d = _accumulation(past, now, 72)
        r7d = _accumulation(past, now, 168)
        
        last_obs_time = past[-1][0]
        data_age_hours = round((now - last_obs_time).total_seconds() / 3600.0, 1)
        quality = "good" if data_age_hours <= 3 else "stale"
        
        return {
            "available": True,
            "timestamp": current.get("time", now.isoformat()),
            "rainfall_1h": round(float(current_value or past[-1][1]), 2),
            "rainfall_24h": r1d,
            "rainfall_1d": r1d,
            "rainfall_3d": r3d,
            "rainfall_7d": r7d,
            "source": "Open-Meteo current/hourly precipitation",
            "is_live": True,
            "data_age_hours": data_age_hours,
            "quality": quality,
            "message": "Live weather observation current",
        }
    except Exception as exc:
        return {
            "available": False,
            "timestamp": now.isoformat(),
            "rainfall_1h": None,
            "rainfall_24h": None,
            "rainfall_1d": None,
            "rainfall_3d": None,
            "rainfall_7d": None,
            "source": f"Live weather stream unavailable ({exc})",
            "is_live": False,
            "data_age_hours": None,
            "quality": "unavailable",
            "message": f"Live weather feed offline: {exc}",
        }


def forecast_rainfall(lat: float, lon: float) -> tuple[list[dict], bool, str]:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    try:
        points = _hourly_points(_open_meteo(lat, lon))
        future = [(timestamp, value) for timestamp, value in points if timestamp > now][:72]
        if len(future) < 72:
            raise ValueError("Incomplete 72-hour forecast returned")
        forecast = [
            {
                "timestamp": timestamp.isoformat(),
                "rainfall": round(rainfall, 2),
                "rainfall_1d": _accumulation(points, timestamp, 24),
                "rainfall_3d": _accumulation(points, timestamp, 72),
                "rainfall_7d": _accumulation(points, timestamp, 168),
            }
            for timestamp, rainfall in future
        ]
        return forecast, True, "Open-Meteo hourly precipitation forecast"
    except Exception as exc:
        fallback = latest_historical_rainfall(lat, lon)
        return [], False, f"IMD historical fallback; forecast source unavailable: {exc}"


def latest_historical_rainfall(lat: float, lon: float) -> dict:
    now = datetime.now(timezone.utc)
    files = sorted(RAIN_DIR.glob("RF25_ind*_rfp25.nc"))
    if not files:
        raise FileNotFoundError("No IMD NetCDF rainfall files are available")
    latest_file = Path(files[-1])
    with xr.open_dataset(latest_file) as dataset:
        point = dataset["RAINFALL"].sel(LATITUDE=lat, LONGITUDE=lon, method="nearest")
        values = np.asarray(point.values, dtype=float)
        values = values[~np.isnan(values)]
        if len(values) == 0:
            raise ValueError("No historical rainfall values are available")

        last_time_value = dataset.TIME.values[-1]
        end = datetime.fromisoformat(str(last_time_value)[:19].replace("T", " ")).replace(tzinfo=timezone.utc)
        data_age_hours = round((now - end).total_seconds() / 3600.0, 1)
        return {
            "available": True,
            "timestamp": end.isoformat(),
            "rainfall_1d": round(float(np.nansum(values[-1:])), 2),
            "rainfall_3d": round(float(np.nansum(values[-3:])), 2),
            "rainfall_7d": round(float(np.nansum(values[-7:])), 2),
            "source": f"IMD NetCDF historical data ({latest_file.stem})",
            "is_live": False,
            "data_age_hours": data_age_hours,
            "quality": "stale",
            "message": "Historical archive dataset (not current weather observation)",
        }
