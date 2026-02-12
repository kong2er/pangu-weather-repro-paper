#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/internal/gen_report.sh"
  echo "Purpose: generate artifacts/day7/REPORT.md with env + checklist."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${ROOT_DIR}/artifacts/day7"
REPORT_PATH="${REPORT_DIR}/REPORT.md"

mkdir -p "${REPORT_DIR}"

PY_PATH="$("${ROOT_DIR}/scripts/run_gpu.sh" -c "import sys; print(sys.executable)")"
ORT_PROVIDERS="$("${ROOT_DIR}/scripts/run_gpu.sh" -c "import onnxruntime as ort; print(ort.get_available_providers())")"

PRODUCT_PNG_COUNT="$(find "${ROOT_DIR}/figures/product" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l | tr -d ' ')"
PRODUCT_JSON_COUNT="$(find "${ROOT_DIR}/figures/product" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l | tr -d ' ')"

cat > "${REPORT_PATH}" <<EOF
# REPORT (A-D Stable Chain + E Alignment)

## Environment
- python: ${PY_PATH}
- onnxruntime providers: ${ORT_PROVIDERS}

## Minimal Chain (commands)
1) scripts/internal/run_day3_smoke_gpu.sh
2) scripts/internal/run_day5_rmse.sh
3) scripts/internal/run_day6_plots.sh
4) scripts/internal/regression_minimal.sh

## Expected Artifacts
- artifacts/day5/rmse.csv
- figures/day6/field_z500_2023070900_t+024.png
- figures/day6/field_z500_2023070900_t+030.png
- figures/day6/rmse_z500_2023070900.png

## E Stage (Product / Streamlit / Geo)
- streamlit entry: pangu_weather_repro/app/app.py
- product bundle cmd:
  \`bash scripts/internal/run_product_bundle.sh --rollout-dir "\$OUTPUT_ROOT/day4_rollout_30h" --vars z500,t2m,u10,v10,msl --hours 24,30\`
- product diff cmd (z500):
  \`bash scripts/internal/run_product_bundle.sh --rollout-dir "\$OUTPUT_ROOT/day4_rollout_30h" --vars z500 --hours 24,30 --kinds fill,diff --force\`
- geo fallback cmd:
  \`scripts/run_gpu.sh tools/plot_product_bundle.py --rollout-dir "\$OUTPUT_ROOT/day4_rollout_30h" --vars z500 --hours 24 --with-geo --geo-assets-dir assets/geo --force\`
- product outputs: png=${PRODUCT_PNG_COUNT}, json=${PRODUCT_JSON_COUNT}

中文说明：
- E阶段默认不覆盖产物，需覆盖请显式加 \`--force\`
- 缺 cartopy/scipy 或缺地理资源时，产品图会自动回退为普通绘图，不中断流程

## Covered Pitfalls
- PYTHONPATH missing in run_smoke_gpu_noarena
- LD_LIBRARY_PATH missing for CUDA libs
- pip logging error (.venv-gpu/bin/pip missing)
- missing netCDF4/cdsapi/matplotlib/cartopy
- plot_fields default rollout/lead mismatch

## Changed Files
- scripts/run_gpu.sh
- scripts/fix_venv_pip.sh
- scripts/create_gpu_venv.sh --update
- scripts/install_extras.sh
- scripts/internal/run_day3_smoke_gpu.sh
- scripts/internal/run_day5_rmse.sh
- scripts/internal/run_day6_plots.sh
- scripts/internal/regression_minimal.sh
- tools/run_smoke_gpu_noarena.py
- tools/eval_rmse.py
- tools/plot_fields.py
- tools/plot_rmse_curve.py
- tools/plot_product_bundle.py
- scripts/internal/run_product_bundle.sh
- scripts/internal/run_e_stage_verify.sh
- pangu_weather_repro/visualization/product_draw.py
- pangu_weather_repro/visualization/geo.py
- tests/test_plot_fields_validation.py
- .github/workflows/ci.yml
- README.md
- RUNBOOK.md
EOF

echo "Wrote ${REPORT_PATH}"
