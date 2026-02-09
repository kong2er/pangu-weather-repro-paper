#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/regression_minimal.sh"
  echo "Purpose: minimal Day3->Day6 regression using existing artifacts."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${ROOT_DIR}/scripts/env_gpu.sh" ]]; then
  source "${ROOT_DIR}/scripts/env_gpu.sh"
fi

if [[ ! -x "${ROOT_DIR}/.venv-gpu/bin/python" ]]; then
  echo "GPU venv missing: ${ROOT_DIR}/.venv-gpu/bin/python"
  echo "Run: make env-gpu"
  exit 1
fi

python -c "import onnxruntime as ort; print('ORT providers:', ort.get_available_providers())" | grep -q CUDAExecutionProvider || {
  echo "CUDAExecutionProvider not available. Run scripts/install_gpu_deps.sh and source scripts/env_gpu.sh"
  exit 2
}

if [[ -z "${OUTPUT_ROOT:-}" ]]; then
  source "${ROOT_DIR}/configs/default.env"
fi

if [[ ! -f "${OUTPUT_ROOT}/day4_rollout_30h/eval_z500.npz" ]]; then
  echo "Missing eval package: ${OUTPUT_ROOT}/day4_rollout_30h/eval_z500.npz"
  echo "Run: scripts/run_gpu.sh tools/day4_rollout.py --steps 24,6 --noarena --out-dir \"${OUTPUT_ROOT}/day4_rollout_30h\""
  exit 3
fi

"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/eval_rmse.py" \
  --pred "${OUTPUT_ROOT}/day4_rollout_30h/eval_z500.npz" \
  --var z500 \
  --out "${ROOT_DIR}/artifacts/day5/rmse.csv"

head -n 3 "${ROOT_DIR}/artifacts/day5/rmse.csv"

"${ROOT_DIR}/scripts/run_day6_plots.sh"

echo "regression_minimal: OK"
