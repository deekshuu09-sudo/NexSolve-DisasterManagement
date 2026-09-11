#!/usr/bin/env bash
# ==============================================================================
# NASADEM Downloader & Authorization Helper for NexSolve
# ==============================================================================
# Works with Earthdata accounts including Google-SSO / Federated Earthdata accounts.
#
# IMPORTANT FOR GOOGLE-FEDERATED EARTHDATA ACCOUNTS:
# 1. Earthdata SSO uses OAuth / Cookie-based session redirect for direct file access.
# 2. Open https://urs.earthdata.nasa.gov in your browser and log in with Google.
# 3. Approve NASADEM / LP DAAC application access if prompted.
# 4. Generate/copy your Earthdata Bearer Token from:
#    https://urs.earthdata.nasa.gov/users/new (or Earthdata profile -> Generate Token)
#    OR pass your Earthdata Username & Password if using native Earthdata login.
#
# USAGE OPTIONS:
# Option A (Token-based download - Recommended for Google SSO):
#   EARTHDATA_TOKEN="your_token_here" ./download_nasadem.sh n23e093
#
# Option B (Interactive login with username/password):
#   ./download_nasadem.sh n23e093
#
# Option C (Direct local drop):
#   Copy downloaded NASADEM_HGT_n23e093.hgt or NASADEM_HGT_n23e093.zip into:
#   backend/data/DEM/
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEM_DIR="${SCRIPT_DIR}/backend/data/DEM"

mkdir -p "${DEM_DIR}"

TILE="${1:-n23e093}"
FILENAME="NASADEM_HGT_${TILE}.hgt"
ZIPNAME="NASADEM_HGT_${TILE}.zip"
URL="https://e4ftl01.cr.usgs.gov/MEASURES/NASADEM_HGT.001/2000.02.11/${ZIPNAME}"

echo "======================================================================"
echo "NASADEM Downloader & Setup Tool"
echo "Target tile: ${TILE} (${ZIPNAME})"
echo "Destination: ${DEM_DIR}"
echo "======================================================================"

if [ -f "${DEM_DIR}/${FILENAME}" ]; then
  echo "SUCCESS: Tile ${FILENAME} already exists in ${DEM_DIR}!"
  exit 0
fi

if [ -f "${DEM_DIR}/${ZIPNAME}" ]; then
  echo "Found ${ZIPNAME} in ${DEM_DIR}, extracting..."
  unzip -o "${DEM_DIR}/${ZIPNAME}" -d "${DEM_DIR}"
  echo "SUCCESS: Extracted ${FILENAME}."
  exit 0
fi

if [ -n "${EARTHDATA_TOKEN}" ]; then
  echo "Downloading using EARTHDATA_TOKEN..."
  curl -f -L -H "Authorization: Bearer ${EARTHDATA_TOKEN}" "${URL}" -o "${DEM_DIR}/${ZIPNAME}"
  if [ -f "${DEM_DIR}/${ZIPNAME}" ]; then
    unzip -o "${DEM_DIR}/${ZIPNAME}" -d "${DEM_DIR}"
    echo "SUCCESS: Downloaded and extracted ${FILENAME}."
    exit 0
  fi
fi

COOKIE_JAR=$(mktemp)

if [ -n "${EARTHDATA_USER}" ] && [ -n "${EARTHDATA_PASS}" ]; then
  echo "Downloading using provided EARTHDATA_USER credentials..."
  curl -f -L -u "${EARTHDATA_USER}:${EARTHDATA_PASS}" -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" "${URL}" -o "${DEM_DIR}/${ZIPNAME}"
  if [ -f "${DEM_DIR}/${ZIPNAME}" ]; then
    unzip -o "${DEM_DIR}/${ZIPNAME}" -d "${DEM_DIR}"
    echo "SUCCESS: Downloaded and extracted ${FILENAME}."
    rm -f "${COOKIE_JAR}"
    exit 0
  fi
fi

rm -f "${COOKIE_JAR}"

echo "----------------------------------------------------------------------"
echo "AUTH REQUIRED FOR ONLINE DOWNLOAD:"
echo "For Google-federated Earthdata accounts:"
echo "1. Log into https://urs.earthdata.nasa.gov in your browser."
echo "2. Authorize LP DAAC / NASA Earthdata if requested."
echo "3. Obtain a Bearer Token or download the file manually."
echo "4. Place the file in: ${DEM_DIR}/${FILENAME} (or ${ZIPNAME})"
echo "----------------------------------------------------------------------"
