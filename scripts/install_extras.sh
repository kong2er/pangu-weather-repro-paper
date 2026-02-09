#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/install_extras.sh {rmse|plots|download|all}"
  echo "Purpose: install optional deps into .venv-gpu."
  exit 0
fi

MODE="${1:-}"
if [[ -z "${MODE}" ]]; then
  echo "Missing mode. Use --help"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-gpu"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "GPU venv not found: ${VENV_DIR}/bin/python"
  echo "Run: make env-gpu"
  exit 1
fi

PIP="${VENV_DIR}/bin/python -m pip"

case "${MODE}" in
  rmse)
    ${PIP} install -U netCDF4 cftime
    ;;
  plots)
    ${PIP} install -U matplotlib cartopy
    ;;
  download)
    ${PIP} install -U cdsapi requests tqdm pyyaml
    ;;
  all)
    ${PIP} install -U netCDF4 cftime matplotlib cartopy cdsapi requests tqdm pyyaml
    ;;
  *)
    echo "Unknown mode: ${MODE}"
    exit 1
    ;;
esac

echo "extras installed: ${MODE}"
