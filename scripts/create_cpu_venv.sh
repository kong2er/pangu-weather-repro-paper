#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/create_cpu_venv.sh"
  echo "Purpose: create .venv-cpu and install project in editable mode."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-cpu"

python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
python -m ensurepip --upgrade
python -m pip install -U pip
python -m pip install -U -e "${ROOT_DIR}"
echo "CPU venv ready: ${VENV_DIR}"
