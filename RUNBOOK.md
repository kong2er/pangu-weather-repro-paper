# RUNBOOK – Pangu-Weather Reproduction (Concise)

目标：可复制、可验证、稳定执行。默认以 30h rollout 为主线。

## 0. 环境准备
CPU：
```bash
cd /root/projects/pangu-weather-repro-uv
scripts/create_cpu_venv.sh
source scripts/env_cpu.sh
scripts/run_cpu.sh -m pangu_weather_repro.smoke
```

GPU：
```bash
cd /root/projects/pangu-weather-repro-uv
scripts/create_gpu_venv.sh
scripts/fix_venv_pip.sh
scripts/install_gpu_deps.sh
scripts/01_download_models.sh
scripts/install_extras.sh rmse
scripts/install_extras.sh plots
source scripts/env_gpu.sh
```

## 1. Day3 → Day6 最小链路（推荐）
```bash
source configs/default.env
scripts/run_day3_smoke_gpu.sh
scripts/run_day5_rmse.sh
scripts/run_day6_plots.sh
scripts/regression_minimal.sh
scripts/gen_report.sh
```

## 2. 数据与模型（Day1–Day2）
```bash
source configs/default.env
bash scripts/01_download_models.sh
scripts/run_gpu.sh scripts/03_download_era5_single.py --date 20230709 --hour 00
scripts/run_gpu.sh scripts/03_download_era5_pressure.py --date 20230709 --hour 00
scripts/run_gpu.sh scripts/03_download_era5_single.py --date 20230709 --hour 06
scripts/run_gpu.sh scripts/03_download_era5_pressure.py --date 20230709 --hour 06
scripts/run_gpu.sh scripts/04_preprocess_era5_to_npy.py --date 20230709 --hour 00
scripts/run_gpu.sh scripts/05_validate_inputs.py
```

## 3. Day4 rollout（30h）
```bash
source configs/default.env
scripts/run_gpu.sh tools/day4_rollout.py --steps 24,6 --noarena --out-dir "$OUTPUT_ROOT/day4_rollout_30h"
```

## 4. Day5 RMSE
```bash
source configs/default.env
scripts/run_day5_rmse.sh
```

## 5. Day6 plots
```bash
source configs/default.env
scripts/run_day6_plots.sh
```

## 6. 对齐推理能力（1/3/6/24 & 1–84 & 84–360）
```bash
source configs/default.env
scripts/run_gpu.sh tools/run_forecast.py --mode short --short-step 1 --target-hours 24
scripts/run_gpu.sh tools/run_forecast.py --mode short --short-step 1 --target-hours 84
scripts/run_gpu.sh tools/run_forecast.py --mode full --short-step 1 --long-step 24 --target-hours 360 --dry-run
```
如遇显存不足（OOM），可加：`--noarena` 或 `--gpu-mem-limit-mb 4096`。

## 7. 论文级图输出
```bash
source configs/default.env
scripts/run_gpu.sh tools/plot_paper_bundle.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --var z500
```

## 8. Region 扩展（示例裁剪）
```bash
scripts/run_cpu.sh tools/region_demo.py --lat-min 28 --lat-max 35 --lon-min 118 --lon-max 123
```

## 9. Day7 metrics（可选）
```bash
source configs/default.env
scripts/run_gpu.sh tools/day7_metrics.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500,t2m,u10 --leads 24 --out artifacts/day7/metrics_summary.csv --md docs/day7_results.md
scripts/run_gpu.sh tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric rmse_latw --out figures/day7/summary_rmse.png
```

## 10. 常见错误与修复
- CPU venv 缺失：`scripts/create_cpu_venv.sh`
- GPU provider 缺失：`scripts/install_gpu_deps.sh && source scripts/env_gpu.sh`
- 模型下载失败：`scripts/01_download_models.sh --no-download`
- netCDF4 缺失：`scripts/install_extras.sh rmse`
- matplotlib/cartopy 缺失：`scripts/install_extras.sh plots`
- 缺 rmse.csv / png：`scripts/regression_minimal.sh`
 - 需要覆盖产物：对应脚本加 `--force`
