# Landslide model training

This folder is intentionally a scaffold until a real, licensed landslide inventory
and environmental feature dataset is supplied.

Expected minimum feature columns:

- `rain24h`
- `soilSat`
- `slopeAngle`
- `gsiEvents`
- `landslide` (binary target)
- timestamp and geographic identifiers for spatial/temporal holdouts

Do not report production accuracy from the current transparent baseline. A trained
artifact should only be placed at `backend/model/artifacts/landslide_model.joblib`
after spatial and temporal validation, precision/recall analysis, calibration,
and false-alarm evaluation.
