#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_product_all.sh [--rollout-dir PATH] [--hours 24,30] [--with-geo] [--force]"
  echo "中文说明: 一键生成 fill/diff/vector/wind_speed/msl_wind 五类产品图，默认不覆盖。"
  echo "Example: scripts/run_product_all.sh --rollout-dir \"\$OUTPUT_ROOT/day4_rollout_30h\" --hours 24,30"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -f "${ROOT_DIR}/configs/default.env" ]]; then
  echo "missing configs/default.env"
  echo "Next: cp configs/default.env.example configs/default.env  # 如无 example 请按 README 创建"
  exit 1
fi
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

if [[ ! -x "${ROOT_DIR}/scripts/run_gpu.sh" ]]; then
  echo "missing scripts/run_gpu.sh"
  echo "Next: git pull --rebase && chmod +x scripts/run_gpu.sh"
  exit 1
fi

if [[ ! -d "${ROLLOUT_DIR}" ]]; then
  echo "rollout_dir not found: ${ROLLOUT_DIR}"
  echo "Next: bash scripts/run_day3_smoke_gpu.sh && bash scripts/run_day5_rmse.sh && bash scripts/run_day6_plots.sh"
  exit 1
fi

if ! "${ROOT_DIR}/scripts/run_gpu.sh" -c "import matplotlib, scipy" >/dev/null 2>&1; then
  echo "missing plotting deps (matplotlib/scipy)"
  echo "Next: bash scripts/install_extras.sh plots"
  exit 1
fi

echo "[STEP] Product all-in-one"
echo "[INPUT] rollout_dir=${ROLLOUT_DIR}"
echo "[HOURS] ${HOURS}"
echo "[OUTPUT] ${ROOT_DIR}/figures/product"
echo "[NEXT] ls -lh ${ROOT_DIR}/figures/product | head -n 20"
if [[ -n "${WITH_GEO}" ]]; then
  echo "[GEO] requested. 若缺 cartopy/地理资源将自动回退到普通绘图（不中断）。"
fi

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

# vector / wind_speed / msl_wind from uv10
bash "${ROOT_DIR}/scripts/run_product_bundle.sh" \
  --rollout-dir "${ROLLOUT_DIR}" \
  --vars u10 \
  --hours "${HOURS}" \
  --kinds vector,wind_speed,msl_wind \
  ${WITH_GEO} \
  ${FORCE}

echo "[DONE] product all-in-one complete"
echo "[NEXT] bash scripts/run_e_stage_verify.sh --force"
