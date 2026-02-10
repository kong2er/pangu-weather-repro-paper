# Pangu-Weather Reproduction (UV + ONNXRuntime)

本仓库用于复现 Pangu-Weather 全球天气预报模型，强调可复现、可工程化与可审计。

## TL;DR
CPU（Day8/CI）：
```bash
cd /root/projects/pangu-weather-repro-uv
scripts/create_cpu_venv.sh
source scripts/env_cpu.sh
scripts/run_cpu.sh -m pangu_weather_repro.smoke
```

GPU（Day3→Day6 最小链路）：
```bash
cd /root/projects/pangu-weather-repro-uv
scripts/create_gpu_venv.sh
scripts/fix_venv_pip.sh
scripts/install_gpu_deps.sh
scripts/install_extras.sh rmse
scripts/install_extras.sh plots
source scripts/env_gpu.sh
source configs/default.env
scripts/regression_minimal.sh
```

一键终验收：
```bash
bash scripts/final_verify.sh
```

默认行为：不覆盖已有产物。需要覆盖时加 `--force`。

## 环境与切换
CPU 环境：`.venv-cpu`（不加载 CUDA）
GPU 环境：`.venv-gpu`（加载 CUDA）

切换：
```bash
source scripts/env_cpu.sh
source scripts/env_gpu.sh
```

注意：不要提交 `.venv-*` 到 Git（已在 `.gitignore`）。

## Quickstart (CPU / Day8)
```bash
scripts/create_cpu_venv.sh
source scripts/env_cpu.sh
scripts/run_cpu.sh -m pangu_weather_repro.smoke
```

## Quickstart (GPU / Day3–Day6 最小链路)
```bash
scripts/create_gpu_venv.sh
scripts/fix_venv_pip.sh
scripts/install_gpu_deps.sh
scripts/01_download_models.sh
scripts/install_extras.sh rmse
scripts/install_extras.sh plots
source scripts/env_gpu.sh
source configs/default.env
scripts/run_day3_smoke_gpu.sh
scripts/run_day5_rmse.sh
scripts/run_day6_plots.sh
```

## 最小链路脚本
- Day3：`scripts/run_day3_smoke_gpu.sh`
- Day5：`scripts/run_day5_rmse.sh`
- Day6：`scripts/run_day6_plots.sh`
- 回归：`scripts/regression_minimal.sh`
- 报告：`scripts/gen_report.sh`

## 对齐能力（zjobsdev/pangu）
- 1/3/6/24h 模型推理：`tools/run_forecast.py --short-step 1|3|6|24 --mode short --target-hours 24`
- 1–84h 逐小时：`tools/run_forecast.py --mode short --short-step 1 --target-hours 84`
- 84–360h 迭代：`tools/run_forecast.py --mode full --short-step 1 --long-step 24 --target-hours 360`
- 仅计划不跑：`tools/run_forecast.py --dry-run --mode full --target-hours 360`

示例（GPU 环境）：
```bash
scripts/run_gpu.sh tools/run_forecast.py --mode short --short-step 1 --target-hours 24
```
如遇显存不足（OOM），可加：
`--noarena` 或 `--gpu-mem-limit-mb 4096`。

## 论文级图输出
```bash
scripts/run_gpu.sh tools/plot_paper_bundle.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --var z500
```

## Region 扩展（可插拔数据适配层）
```bash
scripts/run_cpu.sh tools/region_demo.py --lat-min 28 --lat-max 35 --lon-min 118 --lon-max 123
```

## Troubleshooting（常见错误 → 命令）
- CPU venv 缺失：`scripts/create_cpu_venv.sh`
- CPU 更新：`scripts/create_cpu_venv.sh --update`
- GPU venv 缺失：`scripts/create_gpu_venv.sh`
- GPU provider 缺失 / libcublasLt 缺失：`scripts/install_gpu_deps.sh && source scripts/env_gpu.sh`
- 模型下载失败（网络超时）：
```bash
scripts/01_download_models.sh --no-download
```
或使用 Google Drive 直链（需要 `gdown`，由 `scripts/install_extras.sh download` 安装）：  
```bash
scripts/01_download_models.sh --source gdrive
```
然后把模型手工放到 `MODELS_ROOT`（默认 `/root/autodl-tmp/pangu-weather-repro/models`）。
- 你可以从网盘手动下载以下四个模型并放到上述目录（文件名必须一致）：  
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
- cdsapi 缺失：`scripts/install_extras.sh download`
- rmse.csv 或 day6 png 缺失：`scripts/regression_minimal.sh`
- pip logging error：`scripts/fix_venv_pip.sh`
- 需要覆盖产物：对应脚本加 `--force`

## 产物清单（最小链路）
- `artifacts/day5/rmse.csv`
- `figures/day6/field_z500_2023070900_t+024.png`
- `figures/day6/field_z500_2023070900_t+030.png`
- `figures/day6/rmse_z500_2023070900.png`
- `artifacts/day7/REPORT.md`

## Release
当前收官版本：`v1.0`。详见 `RELEASE_NOTES.md`。

## Full Run（可选，Day1–Day8）
完整流程与排错细节见 `RUNBOOK.md`。
