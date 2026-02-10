#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/create_gpu_venv.sh [--update|--force|--recreate]"
  echo "Purpose: create .venv-gpu and install GPU deps."
  echo "Default: if venv exists, do nothing and print next steps."
  echo "Examples:"
  echo "  scripts/create_gpu_venv.sh"
  echo "  scripts/create_gpu_venv.sh --update"
  echo "  scripts/create_gpu_venv.sh --force"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-gpu"
MODE="${1:-}"

if [[ -x "${VENV_DIR}/bin/python" && "${MODE}" != "--update" && "${MODE}" != "--force" && "${MODE}" != "--recreate" ]]; then
  echo "GPU venv exists: ${VENV_DIR}"
  echo "Use: source scripts/env_gpu.sh"
  echo "To update: scripts/create_gpu_venv.sh --update"
  echo "To recreate: scripts/create_gpu_venv.sh --force"
  exit 0
fi

if [[ "${MODE}" == "--update" && ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "GPU venv missing: ${VENV_DIR}/bin/python"
  echo "Run: scripts/create_gpu_venv.sh"
  exit 1
fi

if [[ "${MODE}" == "--force" || "${MODE}" == "--recreate" ]]; then
  rm -rf "${VENV_DIR}"
fi

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "[STEP] Create GPU venv"
  python3 -m venv "${VENV_DIR}"
fi

echo "[STEP] Install GPU base deps"
"${VENV_DIR}/bin/python" -m ensurepip --upgrade
"${VENV_DIR}/bin/python" -m pip install -U pip
"${VENV_DIR}/bin/python" -m pip install -U -e "${ROOT_DIR}"

echo "[STEP] Install GPU runtime deps"
"${ROOT_DIR}/scripts/install_gpu_deps.sh"
echo "GPU venv ready: ${VENV_DIR}"
