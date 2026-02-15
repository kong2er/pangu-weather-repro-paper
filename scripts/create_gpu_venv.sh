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

# uv 可用性检查
if ! command -v uv >/dev/null 2>&1; then
  echo "[FAIL] uv 未安装。请先安装:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "  或: pip install uv"
  exit 1
fi

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
  echo "[STEP] Create GPU venv (uv)"
  uv venv --python 3.10 "${VENV_DIR}"
fi

echo "[STEP] Install GPU base deps (uv)"
uv pip install --python "${VENV_DIR}/bin/python" -e "${ROOT_DIR}"

echo "[STEP] Install GPU runtime deps"
"${ROOT_DIR}/scripts/internal/install_gpu_deps.sh"
echo "GPU venv ready: ${VENV_DIR}"
