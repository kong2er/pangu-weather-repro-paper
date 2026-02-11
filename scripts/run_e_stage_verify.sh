#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_e_stage_verify.sh [--out FILE] [--force]"
  echo "Purpose: verify E-stage artifacts (streamlit skeleton + product bundle) and write report."
  echo "中文说明: 默认不覆盖报告，传 --force 才覆盖。"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_PATH="${ROOT_DIR}/artifacts/day7/E_STAGE_REPORT.md"
FORCE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      REPORT_PATH="$2"
      shift 2
      ;;
    --force)
      FORCE="1"
      shift 1
      ;;
    *)
      echo "Unknown arg: $1"
      echo "Run: bash scripts/run_e_stage_verify.sh --help"
      exit 1
      ;;
  esac
done

if [[ -f "${REPORT_PATH}" && -z "${FORCE}" ]]; then
  echo "E-stage report exists (skip): ${REPORT_PATH}"
  echo "Next: bash scripts/run_e_stage_verify.sh --force"
  exit 0
fi

mkdir -p "$(dirname "${REPORT_PATH}")"
cd "${ROOT_DIR}"

echo "[STEP] E-stage verify"
echo "[OUTPUT] ${REPORT_PATH}"

APP_ENTRY="${ROOT_DIR}/pangu_weather_repro/app/app.py"
PLOTS_PAGE="${ROOT_DIR}/pangu_weather_repro/app/pages/Plots.py"
PRODUCT_CLI="${ROOT_DIR}/tools/plot_product_bundle.py"
PRODUCT_SCRIPT="${ROOT_DIR}/scripts/run_product_bundle.sh"

have_app="false"
have_product_cli="false"
bundle_status="not_run"
bundle_note=""
vector_status="not_run"
msl_wind_status="not_run"
wind_speed_status="not_run"
extent_status="not_run"

if [[ -f "${APP_ENTRY}" && -f "${PLOTS_PAGE}" ]]; then
  have_app="true"
fi
if [[ -f "${PRODUCT_CLI}" && -f "${PRODUCT_SCRIPT}" ]]; then
  have_product_cli="true"
fi

if [[ -f "${ROOT_DIR}/configs/default.env" ]]; then
  source "${ROOT_DIR}/configs/default.env"
  ROLLOUT_DIR="${OUTPUT_ROOT}/day4_rollout_30h"
else
  ROLLOUT_DIR="${ROOT_DIR}/outputs/day4_rollout_30h"
fi

if [[ "${have_product_cli}" == "true" && -d "${ROLLOUT_DIR}" && -x "${ROOT_DIR}/scripts/run_gpu.sh" ]]; then
  if "${ROOT_DIR}/scripts/run_gpu.sh" "${PRODUCT_CLI}" --rollout-dir "${ROLLOUT_DIR}" --vars z500 --hours 24 >/tmp/e_stage_bundle.log 2>&1; then
    bundle_status="ok"
    bundle_note="ran product bundle (z500, t+24)"
  else
    bundle_status="failed"
    bundle_note="$(tail -n 3 /tmp/e_stage_bundle.log | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g')"
  fi
else
  bundle_status="skipped"
  bundle_note="rollout dir missing, config missing, or product cli/runner unavailable"
fi

if [[ "${have_product_cli}" == "true" && -d "${ROLLOUT_DIR}" && -x "${ROOT_DIR}/scripts/run_gpu.sh" ]]; then
  if "${ROOT_DIR}/scripts/run_gpu.sh" "${PRODUCT_CLI}" --rollout-dir "${ROLLOUT_DIR}" --vars u10 --hours 24 --kinds vector >/tmp/e_stage_vector.log 2>&1; then
    vector_status="ok"
  else
    vector_status="failed"
  fi
  if "${ROOT_DIR}/scripts/run_gpu.sh" "${PRODUCT_CLI}" --rollout-dir "${ROLLOUT_DIR}" --vars u10 --hours 24 --kinds msl_wind >/tmp/e_stage_mslwind.log 2>&1; then
    msl_wind_status="ok"
  else
    msl_wind_status="failed"
  fi
  if "${ROOT_DIR}/scripts/run_gpu.sh" "${PRODUCT_CLI}" --rollout-dir "${ROLLOUT_DIR}" --vars u10 --hours 24 --kinds wind_speed >/tmp/e_stage_windspeed.log 2>&1; then
    wind_speed_status="ok"
  else
    wind_speed_status="failed"
  fi
else
  vector_status="skipped"
  msl_wind_status="skipped"
  wind_speed_status="skipped"
fi

if [[ "${have_product_cli}" == "true" && -d "${ROLLOUT_DIR}" && -x "${ROOT_DIR}/scripts/run_gpu.sh" ]]; then
  if "${ROOT_DIR}/scripts/run_gpu.sh" "${PRODUCT_CLI}" --rollout-dir "${ROLLOUT_DIR}" --vars z500 --hours 24 --kinds fill --extent 95,145,10,50 >/tmp/e_stage_extent.log 2>&1; then
    extent_status="ok"
  else
    extent_status="failed"
  fi
else
  extent_status="skipped"
fi

if [[ -d "${ROOT_DIR}/figures/product" ]]; then
  png_count="$(find "${ROOT_DIR}/figures/product" -maxdepth 1 -name '*.png' | wc -l | tr -d ' ')"
  json_count="$(find "${ROOT_DIR}/figures/product" -maxdepth 1 -name '*.json' | wc -l | tr -d ' ')"
else
  png_count="0"
  json_count="0"
fi

cat > "${REPORT_PATH}" <<EOF
# E Stage Report（E阶段对齐验收）

## Summary
- streamlit_app_files: ${have_app}
- product_bundle_cli: ${have_product_cli}
- product_bundle_check: ${bundle_status}
- product_bundle_note: ${bundle_note}
- product_vector_check: ${vector_status}
- product_msl_wind_check: ${msl_wind_status}
- product_wind_speed_check: ${wind_speed_status}
- product_extent_check: ${extent_status}

## Paths
- app entry: ${APP_ENTRY}
- plots page: ${PLOTS_PAGE}
- product cli: ${PRODUCT_CLI}
- product script: ${PRODUCT_SCRIPT}
- rollout_dir: ${ROLLOUT_DIR}

## Product Outputs
- png_count: ${png_count}
- json_count: ${json_count}

## Quick Commands
\`\`\`bash
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
bash scripts/run_product_all.sh --rollout-dir "\$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force
bash scripts/run_product_bundle.sh --rollout-dir "\$OUTPUT_ROOT/day4_rollout_30h" --vars z500,t2m,u10,v10,msl --hours 24,30
bash scripts/run_product_bundle.sh --rollout-dir "\$OUTPUT_ROOT/day4_rollout_30h" --vars u10 --hours 24,30 --kinds vector,wind_speed,msl_wind
bash scripts/run_product_bundle.sh --rollout-dir "\$OUTPUT_ROOT/day4_rollout_30h" --vars z500 --hours 24 --kinds fill --extent 95,145,10,50 --force
\`\`\`

## Next
- 如果 product_bundle_check=failed：先执行 \`bash scripts/install_extras.sh plots\`，再重试本脚本
- 如果 product_vector_check=failed 或 product_msl_wind_check=failed：先执行 \`bash scripts/install_extras.sh plots --force\`，再重试本脚本
- 如果 product_wind_speed_check=failed：先执行 \`bash scripts/install_extras.sh plots --force\`，再重试本脚本
- 如果 product_extent_check=failed：先确认命令中的 \`--extent\` 为 4 个值（lon_min,lon_max,lat_min,lat_max）
- 如果 rollout 缺失：先完成 Day4 产物，再运行本脚本
EOF

echo "Wrote ${REPORT_PATH}"
echo "[NEXT] sed -n '1,140p' ${REPORT_PATH}"
