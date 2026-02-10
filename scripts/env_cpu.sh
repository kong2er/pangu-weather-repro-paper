#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: source scripts/env_cpu.sh"
  echo "Purpose: set CPU-only environment variables for this repo."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-cpu"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "CPU venv not found: ${VENV_DIR}/bin/python"
  echo "Run: scripts/create_cpu_venv.sh"
  return 1 2>/dev/null || exit 1
fi

export UV_VENV="${VENV_DIR}"
export VIRTUAL_ENV="${VENV_DIR}"
export PATH="${VENV_DIR}/bin:${PATH}"
if [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
  NEW_LD=""
  IFS=":" read -r -a LD_PARTS <<< "${LD_LIBRARY_PATH}"
  for p in "${LD_PARTS[@]}"; do
    if [[ "${p}" == *"/.venv-gpu/"* || "${p}" == *"/nvidia/"* ]]; then
      continue
    fi
    NEW_LD="${NEW_LD}:${p}"
  done
  export LD_LIBRARY_PATH="${NEW_LD#:}"
fi
echo "CPU env active: ${VENV_DIR}"
