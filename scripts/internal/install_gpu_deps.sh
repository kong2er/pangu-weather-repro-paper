#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/install_gpu_deps.sh [--force]"
  echo "Purpose: install onnxruntime-gpu + CUDA cu12 libs into .venv-gpu."
  echo "Default: if deps already present, do nothing."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-gpu"
MODE="${1:-}"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "GPU venv not found: ${VENV_DIR}/bin/python"
  echo "Run: scripts/create_gpu_venv.sh"
  exit 1
fi

VENV_SITE="$("${VENV_DIR}/bin/python" -c "import site; print(site.getsitepackages()[0])")"
CUDA_LIB="${VENV_SITE}/nvidia/cublas/lib/libcublasLt.so.12"

if [[ "${MODE}" != "--force" ]]; then
  if "${VENV_DIR}/bin/python" - <<'PY' >/dev/null 2>&1 && [[ -f "${CUDA_LIB}" ]]; then
import onnxruntime as ort
print(ort.get_available_providers())
PY
    echo "GPU deps already present (skip). Use --force to reinstall."
    exit 0
  fi
fi

uv pip install --python "${VENV_DIR}/bin/python" \
  onnxruntime-gpu==1.23.2 \
  nvidia-cublas-cu12 \
  nvidia-cudnn-cu12 \
  nvidia-cuda-runtime-cu12 \
  nvidia-cuda-nvrtc-cu12 \
  nvidia-cufft-cu12 \
  nvidia-curand-cu12 \
  nvidia-cusolver-cu12 \
  nvidia-cusparse-cu12 \
  nvidia-nvjitlink-cu12

echo "GPU deps installed."
