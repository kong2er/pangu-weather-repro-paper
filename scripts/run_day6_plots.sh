#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_day6_plots.sh"
  echo "Purpose: run Day6 plots for 30h rollout (lead 24/30) and rmse curve."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/configs/default.env"

mkdir -p "${ROOT_DIR}/figures/day6"

if [[ ! -f "${ROOT_DIR}/artifacts/day5/rmse.csv" ]]; then
  echo "rmse.csv not found: ${ROOT_DIR}/artifacts/day5/rmse.csv"
  echo "Run: scripts/run_day5_rmse.sh"
  exit 2
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
