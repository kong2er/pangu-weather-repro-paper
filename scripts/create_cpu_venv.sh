#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/create_cpu_venv.sh [--update|--force|--recreate]"
  echo "Purpose: create .venv-cpu and install project in editable mode."
  echo "Defaults: if venv exists, do nothing and print next steps."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-cpu"
MODE="${1:-}"

if [[ -x "${VENV_DIR}/bin/python" && "${MODE}" != "--update" && "${MODE}" != "--force" && "${MODE}" != "--recreate" ]]; then
  echo "CPU venv exists: ${VENV_DIR}"
  echo "Use: source scripts/env_cpu.sh"
  echo "To update: scripts/create_cpu_venv.sh --update"
  echo "To recreate: scripts/create_cpu_venv.sh --force"
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
echo "CPU venv ready: ${VENV_DIR}"
