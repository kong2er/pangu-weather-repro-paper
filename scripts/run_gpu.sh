#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_gpu.sh <python-args>"
  echo "Example: scripts/run_gpu.sh tools/run_smoke_gpu_noarena.py --step 24"
  echo "Purpose: run commands with .venv-gpu + CUDA libs + PYTHONPATH set."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-gpu"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "GPU venv not found: ${VENV_DIR}/bin/python"
  echo "Run: make env-gpu"
  exit 1
fi

if [[ "$#" -lt 1 ]]; then
  echo "No command provided. Try: scripts/run_gpu.sh --help"
  exit 1
fi

VENV_SITE="$("${VENV_DIR}/bin/python" -c "import site; print(site.getsitepackages()[0])")"

LD_PATHS=(
  "${VENV_SITE}/nvidia/cublas/lib"
  "${VENV_SITE}/nvidia/cudnn/lib"
  "${VENV_SITE}/nvidia/cufft/lib"
  "${VENV_SITE}/nvidia/curand/lib"
  "${VENV_SITE}/nvidia/cusolver/lib"
  "${VENV_SITE}/nvidia/cusparse/lib"
  "${VENV_SITE}/nvidia/cuda_runtime/lib"
  "${VENV_SITE}/nvidia/cuda_nvrtc/lib"
  "${VENV_SITE}/nvidia/nvjitlink/lib"
)

LD_JOIN=""
for d in "${LD_PATHS[@]}"; do
  if [[ -d "${d}" ]]; then
    LD_JOIN="${LD_JOIN}:${d}"
  fi
done

export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"
export LD_LIBRARY_PATH="${LD_JOIN#*:}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"

exec "${VENV_DIR}/bin/python" "$@"
