from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import backend.data.weather_service as weather_service


def test_latest_historical_rainfall_uses_current_time_for_age(monkeypatch):
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])

    class FakeRainfall:
        @staticmethod
        def sel(*args, **kwargs):
            return SimpleNamespace(values=values)

    class FakeDataset:
        TIME = SimpleNamespace(values=np.array(["2026-09-10T00:00:00"], dtype="datetime64[ns]"))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __getitem__(self, key):
            if key == "RAINFALL":
                return FakeRainfall()
            raise KeyError(key)

    class FakeDatetime(datetime):
        @staticmethod
        def now(tz=None):
            return datetime(2026, 9, 11, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(weather_service, "RAIN_DIR", SimpleNamespace(glob=lambda pattern: [Path("dummy.nc")]))
    monkeypatch.setattr(weather_service.xr, "open_dataset", lambda _: FakeDataset())
    monkeypatch.setattr(weather_service, "datetime", FakeDatetime)

    result = weather_service.latest_historical_rainfall(12.5, 87.5)
    assert result["available"] is True
    assert result["data_age_hours"] >= 0


def test_forecast_rainfall_uses_fallback_without_crashing(monkeypatch):
    def boom(lat, lon):
        raise OSError("network timeout")

    monkeypatch.setattr(weather_service, "_open_meteo", boom)
    monkeypatch.setattr(weather_service, "latest_historical_rainfall", lambda lat, lon: {"available": True, "source": "fallback"})

    forecast, is_live, source = weather_service.forecast_rainfall(12.5, 87.5)
    assert forecast == []
    assert is_live is False
    assert "fallback" in source.lower()
