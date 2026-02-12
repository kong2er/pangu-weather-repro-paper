#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/internal/run_day6_plots.sh [--force]"
  echo "Purpose: run Day6 plots for 30h rollout (lead 24/30) and rmse curve."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-}"
source "${ROOT_DIR}/configs/default.env"

mkdir -p "${ROOT_DIR}/figures/day6"

if [[ ! -f "${ROOT_DIR}/artifacts/day5/rmse.csv" ]]; then
  echo "rmse.csv not found: ${ROOT_DIR}/artifacts/day5/rmse.csv"
  echo "Run: scripts/internal/run_day5_rmse.sh"
  exit 2
fi

OUT_24="${ROOT_DIR}/figures/day6/field_z500_2023070900_t+024.png"
OUT_30="${ROOT_DIR}/figures/day6/field_z500_2023070900_t+030.png"
OUT_RMSE="${ROOT_DIR}/figures/day6/rmse_z500_2023070900.png"

echo "[STEP] Day6 plots"
echo "[ENV] GPU (.venv-gpu)"
echo "[INPUT] ${OUTPUT_ROOT}/day4_rollout_30h"
echo "[OUTPUT] ${OUT_24} ${OUT_30} ${OUT_RMSE}"
echo "[NEXT] scripts/final_verify.sh"

if [[ -f "${OUT_24}" && -f "${OUT_30}" && -f "${OUT_RMSE}" && "${MODE}" != "--force" ]]; then
  echo "Day6 plots already exist (skip). Use --force to overwrite."
  ls -lh "${ROOT_DIR}/figures/day6" | head -n 5
  exit 0
fi

"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/plot_fields.py" \
  --rollout-dir "${OUTPUT_ROOT}/day4_rollout_30h" \
  --var z500 \
  --lead 24

"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/plot_fields.py" \
  --rollout-dir "${OUTPUT_ROOT}/day4_rollout_30h" \
  --var z500 \
  --lead 30

"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/plot_rmse_curve.py" \
  --var z500

ls -lh "${ROOT_DIR}/figures/day6" | head -n 5
