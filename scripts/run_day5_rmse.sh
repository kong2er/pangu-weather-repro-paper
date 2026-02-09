#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_day5_rmse.sh"
  echo "Purpose: run Day5 RMSE and show first lines."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/configs/default.env"

"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/eval_rmse.py" \
  --pred "${OUTPUT_ROOT}/day4_rollout_30h/eval_z500.npz" \
  --var z500 \
  --out "${ROOT_DIR}/artifacts/day5/rmse.csv"

head -n 3 "${ROOT_DIR}/artifacts/day5/rmse.csv"
