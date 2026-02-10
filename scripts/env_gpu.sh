#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: source scripts/env_gpu.sh"
  echo "Purpose: set GPU environment variables (LD_LIBRARY_PATH) for this repo."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-gpu"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "GPU venv not found: ${VENV_DIR}/bin/python"
  echo "Run: scripts/create_gpu_venv.sh"
  return 1 2>/dev/null || exit 1
fi

VENV_SITE="$("${VENV_DIR}/bin/python" -c "import site; print(site.getsitepackages()[0])")"
export UV_VENV="${VENV_DIR}"
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"
export PATH="${VENV_DIR}/bin:${PATH}"
export LD_LIBRARY_PATH="${VENV_SITE}/nvidia/cublas/lib:${VENV_SITE}/nvidia/cudnn/lib:${VENV_SITE}/nvidia/cufft/lib:${VENV_SITE}/nvidia/curand/lib:${VENV_SITE}/nvidia/cusolver/lib:${VENV_SITE}/nvidia/cusparse/lib:${VENV_SITE}/nvidia/cuda_runtime/lib:${VENV_SITE}/nvidia/cuda_nvrtc/lib:${VENV_SITE}/nvidia/nvjitlink/lib:${LD_LIBRARY_PATH:-}"
echo "GPU env active: ${VENV_DIR}"
if [[ -f "${VENV_SITE}/nvidia/cublas/lib/libcublasLt.so.12" ]]; then
  echo "CUDA libs: libcublasLt.so.12 OK"
else
  echo "CUDA libs: libcublasLt.so.12 MISSING (run scripts/install_gpu_deps.sh)"
fi
python -c "import onnxruntime as ort; print('ORT providers:', ort.get_available_providers())"
