#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_360h_split.sh [--out-dir PATH] [--gpu-mem-limit-mb N] [--force]"
  echo "Purpose: run 360h split into 84h + 276h using pangu_ref strategy."
  echo "Default: no overwrite, auto timestamp output dir."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/env_gpu.sh"
source "${ROOT_DIR}/configs/default.env"

OUT_DIR=""
MEM_LIMIT=""
FORCE_FLAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --gpu-mem-limit-mb)
      MEM_LIMIT="$2"
      shift 2
      ;;
    --force)
      FORCE_FLAG="--force"
      shift 1
      ;;
    *)
      echo "Unknown arg: $1"
      exit 1
      ;;
  esac
 done

if [[ -z "${OUT_DIR}" ]]; then
  OUT_DIR="/root/autodl-tmp/pangu-weather-repro/outputs/forecast_360h_split_$(date +%Y%m%d_%H%M%S)"
fi

echo "[STEP] 360h forecast split (pangu_ref)"
echo "[ENV] GPU (.venv-gpu)"
echo "[OUTPUT] ${OUT_DIR}_84h and ${OUT_DIR}_276h"

ARGS=(
  "--strategy" "pangu_ref"
  "--mode" "split"
  "--short-step" "6"
  "--long-step" "24"
  "--target-hours" "360"
  "--noarena"
  "--threads" "1"
  "--out-dir" "${OUT_DIR}"
)

if [[ -n "${MEM_LIMIT}" ]]; then
  ARGS+=("--gpu-mem-limit-mb" "${MEM_LIMIT}")
fi

if [[ -n "${FORCE_FLAG}" ]]; then
  ARGS+=("${FORCE_FLAG}")
fi

"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/run_forecast.py" "${ARGS[@]}"
