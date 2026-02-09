#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/install_gpu_deps.sh"
  echo "Purpose: install onnxruntime-gpu + CUDA cu12 libs into .venv-gpu."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-gpu"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "GPU venv not found: ${VENV_DIR}/bin/python"
  echo "Run: make env-gpu"
  exit 1
fi

"${VENV_DIR}/bin/python" -m ensurepip --upgrade
"${VENV_DIR}/bin/python" -m pip install -U \
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
