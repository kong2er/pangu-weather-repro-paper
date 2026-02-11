#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_360h_split.sh [--out-dir PATH] [--gpu-mem-limit-mb N] [--resume-from DIR] [--auto-retry] [--mem-series LIST] [--force]"
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
RESUME_FROM=""
AUTO_RETRY=""
MEM_SERIES=""

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
    --resume-from)
      RESUME_FROM="$2"
      shift 2
      ;;
    --force)
      FORCE_FLAG="--force"
      shift 1
      ;;
    --auto-retry)
      AUTO_RETRY="1"
      shift 1
      ;;
    --mem-series)
      MEM_SERIES="$2"
      shift 2
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
  "--no-cache-sessions"
  "--out-dir" "${OUT_DIR}"
)

if [[ -n "${RESUME_FROM}" ]]; then
  ARGS+=("--resume-from" "${RESUME_FROM}")
fi

if [[ -n "${MEM_LIMIT}" ]]; then
  ARGS+=("--gpu-mem-limit-mb" "${MEM_LIMIT}")
fi

if [[ -n "${FORCE_FLAG}" ]]; then
  ARGS+=("${FORCE_FLAG}")
fi

if [[ -n "${AUTO_RETRY}" ]]; then
  SERIES="${MEM_SERIES:-12288,8192,4096,3072}"
  IFS=',' read -r -a LIMITS <<< "${SERIES}"
  echo "[RETRY] enabled, mem-series=${SERIES}"
  for LIM in "${LIMITS[@]}"; do
    echo "[RETRY] try gpu-mem-limit-mb=${LIM}"
    set +e
    "${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/run_forecast.py" "${ARGS[@]}" --gpu-mem-limit-mb "${LIM}" --resume-from "${OUT_DIR}"
    CODE=$?
    set -e
    if [[ "${CODE}" -eq 0 ]]; then
      echo "[RETRY] success at gpu-mem-limit-mb=${LIM}"
      exit 0
    fi
  done
  echo "[RETRY] all attempts failed. Resume with: scripts/run_360h_split.sh --resume-from ${OUT_DIR}"
  exit 2
else
  "${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/run_forecast.py" "${ARGS[@]}"
fi
