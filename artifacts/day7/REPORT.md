# REPORT (Day3->Day6 Minimal Chain)

## Environment
- python: /root/projects/pangu-weather-repro-uv/.venv-gpu/bin/python
- onnxruntime providers: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']

## Minimal Chain (commands)
1) scripts/run_day3_smoke_gpu.sh
2) scripts/run_day5_rmse.sh
3) scripts/run_day6_plots.sh
4) scripts/regression_minimal.sh

## Expected Artifacts
- artifacts/day5/rmse.csv
- figures/day6/field_z500_2023070900_t+024.png
- figures/day6/field_z500_2023070900_t+030.png
- figures/day6/rmse_z500_2023070900.png

## Covered Pitfalls
- PYTHONPATH missing in run_smoke_gpu_noarena
- LD_LIBRARY_PATH missing for CUDA libs
- pip logging error (.venv-gpu/bin/pip missing)
- missing netCDF4/cdsapi/matplotlib/cartopy
- plot_fields default rollout/lead mismatch

<<<<<<< Updated upstream
## 对齐进度（zjobsdev/pangu）
- 已实现短/长程调度（1–84h / 84–360h）与统一 runner
- tools/run_forecast.py 支持 1/3/6/24h 模型选择
- 论文图包输出（带元数据 JSON，支持 vmin/vmax/cmap 与地图渲染回退）
- RegionDatasetAdapter + region demo 裁剪（支持回填全局网格）

## Day3/4/5 核查记录（中文）
- Day3（GPU Smoke）：通过，输出 `outputs/smoke_24h_report.json`
- Day4（30h Rollout）：通过，产物 `outputs/day4_rollout_30h/eval_z500.npz` + `eval_z500_meta.json`
- Day5（RMSE）：通过，产物 `artifacts/day5/rmse.csv`

## 360h 分段验证（中文）
- 状态：PASS（分段 84h + 276h）
- 短段报告：`outputs/forecast_360h_split_20260211_105104_84h/forecast_report.json`
- 长段报告：`outputs/forecast_360h_split_20260211_105104_276h/forecast_report.json`
- 说明：split 模式避免单次 360h OOM，同时保持 pangu_ref 调度策略；支持 `--resume-from` 续跑不中断
- 稳态建议：若 OOM 频繁，使用 `scripts/run_360h_split.sh --auto-retry` 自动降档显存上限

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

## Changed Files
- scripts/run_gpu.sh
- scripts/fix_venv_pip.sh
- scripts/install_gpu_deps.sh
- scripts/install_extras.sh
- scripts/run_day3_smoke_gpu.sh
- scripts/run_day5_rmse.sh
- scripts/run_day6_plots.sh
- scripts/regression_minimal.sh
- tools/run_smoke_gpu_noarena.py
- tools/eval_rmse.py
- tools/plot_fields.py
- tools/plot_rmse_curve.py
- tests/test_plot_fields_validation.py
- .github/workflows/ci.yml
- README.md

## 收官确认（中文）
- CPU/GPU 最小链路已通过
- 360h split + auto-retry 已通过
- 论文图包已生成（figures/paper）
- Region 适配 demo 已验证
- 推理对齐记录已生成（artifacts/day7/alignment_experiments.md）
 - Region 元数据与回填信息已记录（region_meta.json）
