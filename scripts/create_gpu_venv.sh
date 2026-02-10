#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/create_gpu_venv.sh [--update|--force|--recreate]"
  echo "Purpose: create .venv-gpu and install GPU deps."
  echo "Defaults: if venv exists, do nothing and print next steps."
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

if [[ "${MODE}" == "--force" || "${MODE}" == "--recreate" ]]; then
  rm -rf "${VENV_DIR}"
fi

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m ensurepip --upgrade
"${VENV_DIR}/bin/python" -m pip install -U pip
"${VENV_DIR}/bin/python" -m pip install -U -e "${ROOT_DIR}"

"${ROOT_DIR}/scripts/install_gpu_deps.sh"
echo "GPU venv ready: ${VENV_DIR}"
