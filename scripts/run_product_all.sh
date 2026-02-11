#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_product_all.sh [--rollout-dir PATH] [--hours 24,30] [--with-geo] [--force]"
  echo "中文说明: 一键生成 fill/diff/vector/msl_wind 四类产品图，默认不覆盖。"
  echo "Example: scripts/run_product_all.sh --rollout-dir \"\$OUTPUT_ROOT/day4_rollout_30h\" --hours 24,30"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/configs/default.env"

ROLLOUT_DIR="${OUTPUT_ROOT}/day4_rollout_30h"
HOURS="24,30"
WITH_GEO=""
FORCE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rollout-dir)
      ROLLOUT_DIR="$2"
      shift 2
      ;;
    --hours)
      HOURS="$2"
      shift 2
      ;;
    --with-geo)
      WITH_GEO="--with-geo"
      shift 1
      ;;
    --force)
      FORCE="--force"
      shift 1
      ;;
    *)
      echo "Unknown arg: $1"
      echo "Run: bash scripts/run_product_all.sh --help"
      exit 1
      ;;
  esac
done

echo "[STEP] Product all-in-one"
echo "[INPUT] rollout_dir=${ROLLOUT_DIR}"
echo "[HOURS] ${HOURS}"
echo "[OUTPUT] ${ROOT_DIR}/figures/product"
echo "[NEXT] ls -lh ${ROOT_DIR}/figures/product | head -n 20"

# fill for core vars
bash "${ROOT_DIR}/scripts/run_product_bundle.sh" \
  --rollout-dir "${ROLLOUT_DIR}" \
  --vars z500,t2m,u10,v10,msl \
  --hours "${HOURS}" \
  --kinds fill \
  ${WITH_GEO} \
  ${FORCE}

# diff for z500 (auto fallback to gt_paths if gt_z500 missing)
bash "${ROOT_DIR}/scripts/run_product_bundle.sh" \
  --rollout-dir "${ROLLOUT_DIR}" \
  --vars z500 \
  --hours "${HOURS}" \
  --kinds diff \
  ${FORCE}

# vector and msl_wind from uv10
bash "${ROOT_DIR}/scripts/run_product_bundle.sh" \
  --rollout-dir "${ROLLOUT_DIR}" \
  --vars u10 \
  --hours "${HOURS}" \
  --kinds vector,msl_wind \
  ${WITH_GEO} \
  ${FORCE}

