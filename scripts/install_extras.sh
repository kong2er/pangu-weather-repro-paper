#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/install_extras.sh {rmse|plots|download|streamlit|all} [--force]"
  echo "Purpose: install optional deps into .venv-gpu."
  echo "Default: if deps already present, do nothing."
  exit 0
fi

MODE="${1:-}"
FORCE="${2:-}"
if [[ -z "${MODE}" ]]; then
  echo "Missing mode. Use --help"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-gpu"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "GPU venv not found: ${VENV_DIR}/bin/python"
  echo "Run: scripts/create_gpu_venv.sh"
  exit 1
fi

UV_PIP="uv pip install --python ${VENV_DIR}/bin/python"

case "${MODE}" in
  rmse)
    if [[ "${FORCE}" != "--force" ]]; then
      if "${VENV_DIR}/bin/python" - <<'PY' >/dev/null 2>&1; then
import netCDF4, cftime
PY
        echo "extras already present (rmse). Use --force to reinstall."
        exit 0
      fi
    fi
    ${UV_PIP} netCDF4 cftime
    ;;
  plots)
    if [[ "${FORCE}" != "--force" ]]; then
      if "${VENV_DIR}/bin/python" - <<'PY' >/dev/null 2>&1; then
import matplotlib, cartopy, scipy
PY
        echo "extras already present (plots). Use --force to reinstall."
        exit 0
      fi
    fi
    ${UV_PIP} matplotlib cartopy scipy
    ;;
  download)
    if [[ "${FORCE}" != "--force" ]]; then
      if "${VENV_DIR}/bin/python" - <<'PY' >/dev/null 2>&1; then
import cdsapi, requests, tqdm, yaml, gdown
PY
        echo "extras already present (download). Use --force to reinstall."
        exit 0
      fi
    fi
    ${UV_PIP} cdsapi requests tqdm pyyaml gdown
    ;;
  streamlit)
    if [[ "${FORCE}" != "--force" ]]; then
      if "${VENV_DIR}/bin/python" - <<'PY' >/dev/null 2>&1; then
import streamlit
PY
        echo "extras already present (streamlit). Use --force to reinstall."
        exit 0
      fi
    fi
    ${UV_PIP} streamlit
    ;;
  all)
    if [[ "${FORCE}" != "--force" ]]; then
      if "${VENV_DIR}/bin/python" - <<'PY' >/dev/null 2>&1; then
        import netCDF4, cftime, matplotlib, cartopy, scipy, cdsapi, requests, tqdm, yaml, gdown, streamlit
PY
        echo "extras already present (all). Use --force to reinstall."
        exit 0
      fi
    fi
    ${UV_PIP} netCDF4 cftime matplotlib cartopy scipy cdsapi requests tqdm pyyaml gdown streamlit
    ;;
  *)
    echo "Unknown mode: ${MODE}"
    exit 1
    ;;
esac

echo "extras installed: ${MODE}"
