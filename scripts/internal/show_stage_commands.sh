#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"

cat <<'TXT'
[STAGES] pangu-weather-repro staged commands

S1 环境与依赖
  bash scripts/create_cpu_venv.sh
  bash scripts/create_gpu_venv.sh
  source configs/default.env

S2 CPU smoke
  bash scripts/internal/run_day8_cpu_smoke.sh

S3 GPU smoke
  bash scripts/internal/run_day3_smoke_gpu.sh

S4 84h 推理
  scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --target-hours 84 --noarena --threads 1 --out-dir "$OUTPUT_ROOT/forecast_84h_$(date +%Y%m%d_%H%M%S)"

S5 360h 推理（稳定优先）
  bash scripts/run_360h_split.sh --auto-retry

S6 RMSE + paper 图
  bash scripts/internal/run_day5_rmse.sh
  bash scripts/internal/run_day6_plots.sh

S7 产品图族 + Streamlit
  bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force
  bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501

S8 最终验收
  bash scripts/verify_repo_health.sh
  bash scripts/final_verify.sh --with-e-stage --e-stage-force
  bash scripts/internal/gen_report.sh

[NEXT]
  文档总览: docs/DELIVERY_SUMMARY.md
  蓝本差异: docs/_archive/BLUEPRINT_EQUIV_CHECKLIST.md
  入口矩阵: docs/_archive/ENTRYPOINT_MATRIX.md
  页面映射: docs/_archive/APP_PAGE_MAPPING.md
TXT
