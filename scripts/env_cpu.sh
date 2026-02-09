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
  echo "Run: make env-cpu"
  return 1 2>/dev/null || exit 1
fi

export UV_VENV="${VENV_DIR}"
export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"
export PATH="${VENV_DIR}/bin:${PATH}"
echo "CPU env active: ${VENV_DIR}"
