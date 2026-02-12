#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/fix_venv_pip.sh"
  echo "Purpose: ensure .venv-gpu has pip executable to avoid logging error."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-gpu"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "GPU venv not found: ${VENV_DIR}/bin/python"
  echo "Run: scripts/create_gpu_venv.sh"
  exit 1
fi

"${VENV_DIR}/bin/python" -m ensurepip --upgrade
"${VENV_DIR}/bin/python" -m pip install -U pip

if [[ ! -x "${VENV_DIR}/bin/pip" ]]; then
  ln -sf "${VENV_DIR}/bin/python" "${VENV_DIR}/bin/pip"
fi

"${VENV_DIR}/bin/python" -m pip --version
echo "pip ok: ${VENV_DIR}/bin/pip"
