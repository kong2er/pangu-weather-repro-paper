# REPORT (Day3–Day8 Stable Repro + Alignment Progress)

## 环境
- CPU smoke：`scripts/run_day8_cpu_smoke.sh`
- GPU 最小链路：`scripts/run_day3_smoke_gpu.sh` → `scripts/run_day5_rmse.sh` → `scripts/run_day6_plots.sh`

## 稳定链路（命令）
1) scripts/run_day8_cpu_smoke.sh
2) scripts/run_day3_smoke_gpu.sh
3) scripts/run_day5_rmse.sh
4) scripts/run_day6_plots.sh
5) scripts/final_verify.sh

## 预期产物
- artifacts/day5/rmse.csv
- figures/day6/field_z500_2023070900_t+024.png
- figures/day6/field_z500_2023070900_t+030.png
- figures/day6/rmse_z500_2023070900.png
- artifacts/day7/reference_diff_report.md

## 稳定性改造（已完成）
- CPU/GPU venv 幂等创建（支持 --update/--force）
- run_cpu.sh / run_gpu.sh 强制正确解释器与 PYTHONPATH
- env_cpu.sh 清理 CUDA 路径；env_gpu.sh 校验 CUDA 库与 providers
- Day5/Day6 默认不覆盖产物，需 --force 才覆盖
- 依赖提示统一指向 scripts/install_extras.sh

## 对齐进度（zjobsdev/pangu）
- 已实现短/长程调度（1–84h / 84–360h）与统一 runner
- tools/run_forecast.py 支持 1/3/6/24h 模型选择
- 论文图包输出（带元数据 JSON，支持 vmin/vmax/cmap 与地图渲染回退）
- RegionDatasetAdapter + region demo 裁剪

## Day3/4/5 核查记录（中文）
- Day3（GPU Smoke）：通过，输出 `outputs/smoke_24h_report.json`
- Day4（30h Rollout）：通过，产物 `outputs/day4_rollout_30h/eval_z500.npz` + `eval_z500_meta.json`
- Day5（RMSE）：通过，产物 `artifacts/day5/rmse.csv`

## 360h 分段验证（中文）
- 状态：PASS（分段 84h + 276h）
- 短段报告：`outputs/forecast_360h_split_20260210_220939_84h/forecast_report.json`
- 长段报告：`outputs/forecast_360h_split_20260210_220939_276h/forecast_report.json`
- 说明：split 模式避免单次 360h OOM，同时保持 pangu_ref 调度策略

## 变更文件（关键）
- pangu_weather_repro/infer/*
- pangu_weather_repro/region/*
- tools/run_forecast.py
- tools/plot_paper_bundle.py
- tools/region_demo.py
- tools/plot_fields.py
- scripts/create_cpu_venv.sh
- scripts/create_gpu_venv.sh
- scripts/env_cpu.sh
- scripts/env_gpu.sh
- scripts/run_cpu.sh
- scripts/run_gpu.sh
- scripts/run_day3_smoke_gpu.sh
- scripts/run_day5_rmse.sh
- scripts/run_day6_plots.sh
- scripts/run_day8_cpu_smoke.sh
- scripts/final_verify.sh
- scripts/install_gpu_deps.sh
- scripts/install_extras.sh
- scripts/vendor_sync_reference.sh
- docs/GAP_REPORT.md
- docs/reference_pangu.md
- README.md
- RUNBOOK.md
