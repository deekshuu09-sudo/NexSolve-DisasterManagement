# Official Survey of India (ABDB) Spatial Boundary Provenance

This directory contains official administrative boundaries for the 8 North Eastern States of India and their 131 districts, extracted and reprojected directly from the official **Survey of India Administrative Boundary Data-Base (ABDB)**.

---

## 1. Official Dataset Source

* **Product Name**: State / District / Sub-District Boundary Data-Base of India (ABDB)
* **Source URL**: `https://surveyofindia.gov.in/documents/State_District_Subdistrict_PAN%20INDIA.rar`
* **Local Archive**: `State_District_Subdistrict_PAN_INDIA.rar`
* **Archive Size**: 202,524,438 bytes
* **Archive SHA-256**: `b8325e5d9dd0f04a6663d775363fe38cd2f23bd9dbae3fb7118b4e6e0ce0bcb7`
* **Source Shapefiles Used**:
  * `State Boundary/State Boundary.shp` (40 total features across India)
  * `District_Subdistrict_PAN INDIA/District Boundary.shp` (808 total features across India)

---

## 2. Spatial Projection & Reprojection

* **Original Projection**: Lambert Conformal Conic (LCC WGS84)
  * `Central_Meridian`: 80.0
  * `Latitude_Of_Origin`: 24.0
  * `Standard_Parallel_1`: 12.472944
  * `Standard_Parallel_2`: 35.172806
  * `False_Easting`: 4,000,000.0 meters
  * `False_Northing`: 4,000,000.0 meters
* **Target Coordinate Reference System**: `EPSG:4326` (WGS84 Geodetic Latitude / Longitude)
* **Reprojection Tool**: `pyproj.Transformer` / `shapely.ops.transform` (`convert_soi_geojson.py`)

---

## 3. Scope & Attribute Normalization

### Northeast India Coverage
Only the 8 official Northeast India states and their 131 districts were extracted:

| State | Official LGD Code | District Count |
| :--- | :--- | :--- |
| **Arunachal Pradesh** | 12 | 27 |
| **Assam** | 18 | 35 |
| **Manipur** | 14 | 16 |
| **Meghalaya** | 17 | 12 |
| **Mizoram** | 15 | 11 |
| **Nagaland** | 13 | 16 |
| **Sikkim** | 11 | 6 |
| **Tripura** | 16 | 8 |
| **Total** | | **131** |

### Preserved Official Fields
All original attributes from the Survey of India DBF tables are preserved:
* `STATE_UT`, `STATE_LGD`
* `DISTRICT`, `DIST_LGD`
* `REMARKS`, `OBJECTID`, `Shape_Leng`, `Shape_Area`

### Text Encoding & Diacritic Cleaning
The official Survey of India DBF tables represent diacritical placeholders using `>`. These are normalized into standard text representations while retaining original `DISTRICT` and `STATE_UT` strings:
* `>NJ>W` $\rightarrow$ `Anjaw` (Original SOI preserved in `district_name_soi`)
* `CH>NGL>NG` $\rightarrow$ `Changlang`
* `DIB>NG VALLEY` $\rightarrow$ `Dibang Valley`
* `EAST G>RO HILLS` $\rightarrow$ `East Garo Hills`
* `EAST KH>SI HILLS` $\rightarrow$ `East Khasi Hills`

---

## 4. Output Files & Validation Summary

### Created GeoJSON Datasets
1. `ner_states_soi.geojson`:
   * **Feature Count**: 8
   * **Geometry Type**: Polygon / MultiPolygon
   * **Bounding Box**: Longitude `[88.0123° E, 97.4129° E]`, Latitude `[21.9400° N, 29.4659° N]`
   * **Geometry Validity**: 100% Valid (`shapely.is_valid`), 0 Null geometries

2. `ner_districts_soi.geojson`:
   * **Feature Count**: 131
   * **Geometry Type**: Polygon / MultiPolygon
   * **Bounding Box**: Longitude `[88.0123° E, 97.4129° E]`, Latitude `[21.9400° N, 29.4659° N]`
   * **Geometry Validity**: 100% Valid (`shapely.is_valid`), 0 Null geometries

---

## 5. System Integrity & Safety

* **ML Model Integrity**: `backend/model/landslide_model.pkl` remains completely untouched and un-modified.
* **Third-Party Data Prohibition**: Zero data from OpenStreetMap, Kaggle, GADM, Natural Earth, or any unverified third party was used.
