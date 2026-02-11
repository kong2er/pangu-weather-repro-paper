#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_product_bundle.sh [--force] [--with-geo] [--vars z500,t2m,u10] [--hours 24,30] [--kinds fill,diff,vector,msl_wind] [--rollout-dir PATH]"
  echo "中文说明: 生成产品图（figures/product/*.png + *.json），默认不覆盖。"
  echo "Example: scripts/run_product_bundle.sh --vars z500,t2m --hours 24,30"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/configs/default.env"

echo "[STEP] Product bundle"
echo "[ENV] GPU (.venv-gpu)"
echo "[INPUT] OUTPUT_ROOT=${OUTPUT_ROOT}"
echo "[OUTPUT] ${ROOT_DIR}/figures/product"
echo "[NEXT] ls -lh ${ROOT_DIR}/figures/product | head"

"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/plot_product_bundle.py" "$@"
