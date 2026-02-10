#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_day5_rmse.sh [--force]"
  echo "Purpose: run Day5 RMSE and show first lines."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-}"
source "${ROOT_DIR}/configs/default.env"

OUT_CSV="${ROOT_DIR}/artifacts/day5/rmse.csv"
PRED_NPZ="${OUTPUT_ROOT}/day4_rollout_30h/eval_z500.npz"
mkdir -p "${ROOT_DIR}/artifacts/day5"

echo "[STEP] Day5 RMSE"
echo "[ENV] GPU (.venv-gpu)"
echo "[INPUT] ${PRED_NPZ}"
echo "[OUTPUT] ${OUT_CSV}"
echo "[NEXT] scripts/run_day6_plots.sh"

if [[ ! -f "${PRED_NPZ}" ]]; then
  echo "Missing eval package: ${PRED_NPZ}"
  echo "Run: scripts/run_gpu.sh tools/day4_rollout.py --steps 24,6 --noarena --out-dir \"${OUTPUT_ROOT}/day4_rollout_30h\""
  exit 2
fi

if [[ -f "${OUT_CSV}" && "${MODE}" != "--force" ]]; then
  echo "rmse.csv exists (skip). Use --force to overwrite."
  head -n 3 "${OUT_CSV}"
  exit 0
fi

"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/eval_rmse.py" \
  --pred "${PRED_NPZ}" \
  --var z500 \
  --out "${OUT_CSV}"

head -n 3 "${OUT_CSV}"
