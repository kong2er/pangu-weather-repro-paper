#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/create_cpu_venv.sh [--update|--force|--recreate]"
  echo "Purpose: create .venv-cpu and install project in editable mode."
  echo "Default: if venv exists, do nothing and print next steps."
  echo "Examples:"
  echo "  scripts/create_cpu_venv.sh"
  echo "  scripts/create_cpu_venv.sh --update"
  echo "  scripts/create_cpu_venv.sh --force"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-cpu"
MODE="${1:-}"

# uv 可用性检查
if ! command -v uv >/dev/null 2>&1; then
  echo "[FAIL] uv 未安装。请先安装:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "  或: pip install uv"
  exit 1
fi

if [[ -x "${VENV_DIR}/bin/python" && "${MODE}" != "--update" && "${MODE}" != "--force" && "${MODE}" != "--recreate" ]]; then
  echo "CPU venv exists: ${VENV_DIR}"
  echo "Use: source scripts/env_cpu.sh"
  echo "To update: scripts/create_cpu_venv.sh --update"
  echo "To recreate: scripts/create_cpu_venv.sh --force"
  exit 0
fi

if [[ "${MODE}" == "--update" && ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "CPU venv missing: ${VENV_DIR}/bin/python"
  echo "Run: scripts/create_cpu_venv.sh"
  exit 1
fi

if [[ "${MODE}" == "--force" || "${MODE}" == "--recreate" ]]; then
  rm -rf "${VENV_DIR}"
fi

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "[STEP] Create CPU venv (uv)"
  uv venv --python 3.10 "${VENV_DIR}"
fi

echo "[STEP] Install CPU deps (uv)"
uv pip install --python "${VENV_DIR}/bin/python" -e "${ROOT_DIR}"
echo "CPU venv ready: ${VENV_DIR}"
