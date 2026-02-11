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
scripts/run_gpu.sh tools/run_forecast.py --strategy pangu_ref --mode short --short-step 1 --target-hours 24
scripts/run_gpu.sh tools/run_forecast.py --strategy pangu_ref --mode short --short-step 1 --target-hours 84
scripts/run_gpu.sh tools/run_forecast.py --strategy pangu_ref --mode full --short-step 1 --long-step 24 --target-hours 360 --dry-run
```
如遇显存不足（OOM），可加：`--noarena` 或 `--gpu-mem-limit-mb 4096`。
推荐 360h 稳定跑法（分段）：
```bash
scripts/run_360h_split.sh
```
更稳（限制显存上限）：
```bash
scripts/run_360h_split.sh --gpu-mem-limit-mb 4096
```
断连/失败后续跑（不覆盖）：
```bash
scripts/run_360h_split.sh --resume-from /root/autodl-tmp/pangu-weather-repro/outputs/forecast_360h_split_YYYYMMDD_HHMMSS
```

## 7. 论文级图输出
```bash
source configs/default.env
scripts/run_gpu.sh tools/plot_paper_bundle.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --var z500
```
提示：支持 `--no-map`、`--cmap`、`--vmin/--vmax`、`--dpi`；若缺 cartopy，会自动回退到无地图绘制。

## 8. Region 扩展（示例裁剪）
```bash
scripts/run_cpu.sh tools/region_demo.py --lat-min 28 --lat-max 35 --lon-min 118 --lon-max 123
```
需要回填到全局网格（对齐模型输入形状）：
```bash
scripts/run_cpu.sh tools/region_demo.py --lat-min 28 --lat-max 35 --lon-min 118 --lon-max 123 --pad-to-global --fill-value 0.0
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
  或：`scripts/01_download_models.sh --source gdrive`（默认无需 gdown，脚本内置回退）
  手动放置模型到 `MODELS_ROOT`（默认 `/root/autodl-tmp/pangu-weather-repro/models`）：
  `pangu_weather_1.onnx` / `pangu_weather_3.onnx` / `pangu_weather_6.onnx` / `pangu_weather_24.onnx`
  参考入口（在代码块内，便于复制）：
```text
https://github.com/HaxyMoly/Pangu-Weather-ReadyToGo
https://github.com/198808xc/Pangu-Weather/tree/main#global-weather-forecasting-inference-using-the-trained-models
```
  直接下载（Google Drive，按 1/3/6/24 顺序）：
```text
1h:  https://drive.google.com/file/d/1fg5jkiN_5dHzKb-5H9Aw4MOmfILmeY-S/view?usp=sharing
3h:  https://drive.google.com/file/d/1EdoLlAXqE9iZLt9Ej9i-JW9LTJ9Jtewt/view?usp=sharing
6h:  https://drive.google.com/file/d/1a4XTktkZa5GCtjQxDJb_fNaqTAUiEJu4/view?usp=sharing
24h: https://drive.google.com/file/d/1lweQlxcn9fG0zKNW8ne1Khr9ehRTI6HP/view?usp=sharing
```
- netCDF4 缺失：`scripts/install_extras.sh rmse`
- matplotlib/cartopy 缺失：`scripts/install_extras.sh plots`
- 缺 rmse.csv / png：`scripts/regression_minimal.sh`
 - 需要覆盖产物：对应脚本加 `--force`
