#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: scripts/prepare_era5_inputs.sh [--date YYYYMMDD] [--hour HH] [--yes] [--dataset-mode default|custom] [--force-preprocess]
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
- Interactive guard:
  yes  -> follow project default dataset and auto-download when needed
  no   -> use custom dataset (script stops and asks you to place files manually)
EOF
  exit 0
fi

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/configs/default.env"

DATE_ARG="${DATE}"
HOUR_ARG="${HOUR}"
DATASET_MODE=""
ASSUME_YES=0
FORCE_PREPROCESS=0
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
    --dataset-mode)
      DATASET_MODE="${2:?missing value for --dataset-mode}"
      shift 2
      ;;
    --yes)
      ASSUME_YES=1
      DATASET_MODE="default"
      shift 1
      ;;
    --force-preprocess)
      FORCE_PREPROCESS=1
      shift 1
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

if [[ -z "${DATASET_MODE}" ]]; then
  if [[ "${ASSUME_YES}" -eq 1 ]]; then
    DATASET_MODE="default"
  elif [[ -t 0 ]]; then
    read -r -p "[QUESTION] Follow default project dataset? (yes/no): " REPLY
    case "${REPLY}" in
      yes|y|Y)
        DATASET_MODE="default"
        ;;
      no|n|N)
        DATASET_MODE="custom"
        ;;
      *)
        echo "[FAIL] Please answer yes or no."
        exit 2
        ;;
    esac
  else
    DATASET_MODE="default"
  fi
fi

if [[ "${DATASET_MODE}" != "default" && "${DATASET_MODE}" != "custom" ]]; then
  echo "[FAIL] --dataset-mode must be default or custom"
  exit 2
fi

if [[ ! -f "${SINGLE_NC}" || ! -f "${PRESSURE_NC}" ]]; then
  if [[ "${DATASET_MODE}" == "custom" ]]; then
    cat <<EOF
[STOP] custom dataset mode selected.
[NEED] place your dataset files as:
  ${SINGLE_NC}
  ${PRESSURE_NC}
Then rerun:
  bash scripts/prepare_era5_inputs.sh --dataset-mode custom
EOF
    exit 1
  fi
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

SURFACE_NPY="${PROCESSED_ROOT}/surface.npy"
PRESSURE_NPY="${PROCESSED_ROOT}/pressure.npy"
if [[ "${FORCE_PREPROCESS}" -eq 0 && -s "${SURFACE_NPY}" && -s "${PRESSURE_NPY}" ]]; then
  echo "[STEP] processed npy already present (skip preprocess)"
else
  echo "[STEP] preprocess ERA5 nc -> numpy"
  "${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/04_preprocess_era5_to_npy.py" \
    --date "${DATE_ARG}" --hour "${HOUR_ARG}" --raw-dir "${ERA5_RAW_ROOT}" --out-dir "${PROCESSED_ROOT}"
fi

echo "[STEP] validate processed inputs"
"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/05_validate_inputs.py" \
  --processed-dir "${PROCESSED_ROOT}"

echo "[PASS] ERA5 inputs ready"
echo "[OUTPUT] ${PROCESSED_ROOT}/surface.npy"
echo "[OUTPUT] ${PROCESSED_ROOT}/pressure.npy"
