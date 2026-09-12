import pandas as pd
import xarray as xr
import numpy as np
from pathlib import Path

LANDSLIDE_FILE = Path("backend/data/landslides/ner_landslides.csv")
RAINFALL_DIR = Path("backend/data/rainfall/RF25_ind2014_2025")
OUTPUT_FILE = Path("backend/data/training/landslide_rainfall_dataset.csv")

# -----------------------------
# Load landslide data
# -----------------------------
df = pd.read_csv(LANDSLIDE_FILE)

df["history"] = df["history"].astype(str).str.strip()

# Keep only records with exact dates
date_pattern = r"^\d{1,2} [A-Za-z]+ \d{4}$"
df = df[df["history"].str.match(date_pattern, na=False)].copy()

df["date"] = pd.to_datetime(
    df["history"],
    format="%d %B %Y",
    errors="coerce"
)

df = df.dropna(subset=["date", "latitude", "longitude"])

print(f"Landslide records with exact dates: {len(df)}")

# -----------------------------
# Process rainfall year by year
# -----------------------------
results = []

for year in sorted(df["date"].dt.year.unique()):

    rainfall_file = (
        RAINFALL_DIR /
        f"RF25_ind{year}_rfp25.nc"
    )

    if not rainfall_file.exists():
        print(f"Skipping {year}: rainfall file not found")
        continue

    print(f"Processing rainfall: {year}")

    ds = xr.open_dataset(rainfall_file)

    rain = ds["RAINFALL"]

    year_df = df[df["date"].dt.year == year].copy()

    # ---------------------------------
    # Match each landslide to nearest
    # rainfall grid point
    # ---------------------------------
    daily_values = []

    for _, row in year_df.iterrows():

        lat_idx = np.abs(
            ds["LATITUDE"].values - row["latitude"]
        ).argmin()

        lon_idx = np.abs(
            ds["LONGITUDE"].values - row["longitude"]
        ).argmin()

        date_idx = np.where(
            ds["TIME"].dt.date.values == row["date"].date()
        )[0]

        if len(date_idx) == 0:
            daily_values.append(
                [np.nan, np.nan, np.nan]
            )
            continue

        t = date_idx[0]

        # 1-day rainfall
        r1 = float(
            rain.isel(
                TIME=t,
                LATITUDE=lat_idx,
                LONGITUDE=lon_idx
            ).values
        )

        # 3-day rainfall
        start3 = max(0, t - 2)

        r3 = float(
            rain.isel(
                TIME=slice(start3, t + 1),
                LATITUDE=lat_idx,
                LONGITUDE=lon_idx
            ).sum(skipna=True).values
        )

        # 7-day rainfall
        start7 = max(0, t - 6)

        r7 = float(
            rain.isel(
                TIME=slice(start7, t + 1),
                LATITUDE=lat_idx,
                LONGITUDE=lon_idx
            ).sum(skipna=True).values
        )

        daily_values.append([r1, r3, r7])

    year_df[
        ["rainfall_1d", "rainfall_3d", "rainfall_7d"]
    ] = daily_values

    results.append(year_df)

    ds.close()

# -----------------------------
# Combine everything
# -----------------------------
if not results:
    raise RuntimeError("No matching rainfall data found.")

final_df = pd.concat(results, ignore_index=True)

# -----------------------------
# Save
# -----------------------------
OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

final_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n==============================")
print("TRAINING DATASET CREATED")
print("==============================")
print(f"Rows: {len(final_df)}")
print(f"Columns: {len(final_df.columns)}")
print(f"Saved to: {OUTPUT_FILE}")
print("\nColumns:")
print(final_df.columns.tolist())