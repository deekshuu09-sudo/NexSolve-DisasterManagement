from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr


RAIN_DIR = (
    Path(__file__).resolve().parent
    / "rainfall"
    / "RF25_ind2014_2025"
)


def get_rainfall(lat: float, lon: float, date: str):
    """
    Get IMD gridded rainfall for the nearest grid cell.

    Returns:
        rainfall_1d
        rainfall_3d
        rainfall_7d
    """

    target_date = pd.Timestamp(date)
    year = target_date.year

    file_path = RAIN_DIR / f"RF25_ind{year}_rfp25.nc"

    if not file_path.exists():
        raise FileNotFoundError(
            f"IMD rainfall file not found for {year}: {file_path}"
        )

    ds = xr.open_dataset(file_path)

    try:
        # Select nearest IMD 0.25° grid cell
        point = ds["RAINFALL"].sel(
            LATITUDE=lat,
            LONGITUDE=lon,
            method="nearest"
        )

        # Select rainfall dates up to requested date
        values = point.sel(
            TIME=slice(None, target_date)
        ).values

        if len(values) == 0:
            raise ValueError(
                f"No rainfall data available before {date}"
            )

        # Last 1 / 3 / 7 days
        rainfall_1d = float(np.nansum(values[-1:]))
        rainfall_3d = float(np.nansum(values[-3:]))
        rainfall_7d = float(np.nansum(values[-7:]))

        return {
            "rainfall_1d": round(rainfall_1d, 2),
            "rainfall_3d": round(rainfall_3d, 2),
            "rainfall_7d": round(rainfall_7d, 2),
        }

    finally:
        ds.close()