#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/internal/regression_minimal.sh"
  echo "Purpose: minimal Day3->Day6 regression using existing artifacts."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${ROOT_DIR}/scripts/env_gpu.sh" ]]; then
  source "${ROOT_DIR}/scripts/env_gpu.sh"
fi

if [[ ! -x "${ROOT_DIR}/.venv-gpu/bin/python" ]]; then
  echo "GPU venv missing: ${ROOT_DIR}/.venv-gpu/bin/python"
  echo "Run: scripts/create_gpu_venv.sh"
  exit 1
fi

${ROOT_DIR}/scripts/run_gpu.sh -c "import onnxruntime as ort; print('ORT providers:', ort.get_available_providers())" | grep -q CUDAExecutionProvider || {
  echo "CUDAExecutionProvider not available. Run scripts/create_gpu_venv.sh --update and source scripts/env_gpu.sh"
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

"${ROOT_DIR}/scripts/internal/run_day5_rmse.sh"
"${ROOT_DIR}/scripts/internal/run_day6_plots.sh"

echo "regression_minimal: OK"
