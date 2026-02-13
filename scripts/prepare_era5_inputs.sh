#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: scripts/prepare_era5_inputs.sh [--date YYYYMMDD] [--hour HH]
Purpose: prepare Day3 GPU smoke inputs (surface.npy + pressure.npy).

What it does:
1) download ERA5 single/pressure nc to ERA5_RAW_ROOT
2) preprocess nc -> PROCESSED_ROOT/{surface.npy,pressure.npy}
3) validate processed inputs

Notes:
- Requires ~/.cdsapirc for CDS API download.
- If your network cannot access CDS, place nc files manually:
  ERA5_RAW_ROOT/era5_single_<date><hour>.nc
  ERA5_RAW_ROOT/era5_pressure_<date><hour>.nc
EOF
  exit 0
fi

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/configs/default.env"

DATE_ARG="${DATE}"
HOUR_ARG="${HOUR}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --date)
      DATE_ARG="${2:?missing value for --date}"
      shift 2
      ;;
    --hour)
      HOUR_ARG="${2:?missing value for --hour}"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1"
      echo "Try: scripts/prepare_era5_inputs.sh --help"
      exit 2
      ;;
  esac
done

SINGLE_NC="${ERA5_RAW_ROOT}/era5_single_${DATE_ARG}${HOUR_ARG}.nc"
PRESSURE_NC="${ERA5_RAW_ROOT}/era5_pressure_${DATE_ARG}${HOUR_ARG}.nc"

mkdir -p "${ERA5_RAW_ROOT}" "${PROCESSED_ROOT}"

if [[ ! -f "${SINGLE_NC}" || ! -f "${PRESSURE_NC}" ]]; then
  if [[ ! -f "${HOME}/.cdsapirc" ]]; then
    cat <<EOF
[FAIL] missing ~/.cdsapirc and ERA5 nc files not found.
[NEED] either:
  1) configure ~/.cdsapirc then rerun this script
  2) manually place:
     ${SINGLE_NC}
     ${PRESSURE_NC}
EOF
    exit 1
  fi
  echo "[STEP] download ERA5 single-level nc"
  "${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/03_download_era5_single.py" \
    --date "${DATE_ARG}" --hour "${HOUR_ARG}" --out-dir "${ERA5_RAW_ROOT}"
  echo "[STEP] download ERA5 pressure-level nc"
  "${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/03_download_era5_pressure.py" \
    --date "${DATE_ARG}" --hour "${HOUR_ARG}" --out-dir "${ERA5_RAW_ROOT}"
else
  echo "[STEP] ERA5 nc already present (skip download)"
fi

echo "[STEP] preprocess ERA5 nc -> numpy"
"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/04_preprocess_era5_to_npy.py" \
  --date "${DATE_ARG}" --hour "${HOUR_ARG}" --raw-dir "${ERA5_RAW_ROOT}" --out-dir "${PROCESSED_ROOT}"

echo "[STEP] validate processed inputs"
"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/05_validate_inputs.py" \
  --processed-dir "${PROCESSED_ROOT}"

echo "[PASS] ERA5 inputs ready"
echo "[OUTPUT] ${PROCESSED_ROOT}/surface.npy"
echo "[OUTPUT] ${PROCESSED_ROOT}/pressure.npy"
