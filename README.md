# Pangu-Weather Reproduction (UV + ONNXRuntime)

本仓库用于复现 Pangu-Weather 全球天气预报模型，强调可复现、可工程化与可审计。

## TL;DR
CPU（Day8/CI）：
```bash
cd /root/projects/pangu-weather-repro-uv
scripts/create_cpu_venv.sh
source scripts/env_cpu.sh
python -m pangu_weather_repro.smoke
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
python -m pangu_weather_repro.smoke
```

## Quickstart (GPU / Day3–Day6 最小链路)
```bash
scripts/create_gpu_venv.sh
scripts/fix_venv_pip.sh
scripts/install_gpu_deps.sh
scripts/install_extras.sh rmse
scripts/install_extras.sh plots
source scripts/env_gpu.sh
source configs/default.env
scripts/regression_minimal.sh
```

## 最小链路脚本
- Day3：`scripts/run_day3_smoke_gpu.sh`
- Day5：`scripts/run_day5_rmse.sh`
- Day6：`scripts/run_day6_plots.sh`
- 回归：`scripts/regression_minimal.sh`
- 报告：`scripts/gen_report.sh`

## Troubleshooting（常见错误 → 命令）
- CPU venv 缺失：`scripts/create_cpu_venv.sh`
- CPU 更新：`scripts/create_cpu_venv.sh --update`
- GPU venv 缺失：`scripts/create_gpu_venv.sh`
- GPU provider 缺失 / libcublasLt 缺失：`scripts/install_gpu_deps.sh && source scripts/env_gpu.sh`
- netCDF4 缺失：`scripts/install_extras.sh rmse`
- matplotlib/cartopy 缺失：`scripts/install_extras.sh plots`
- cdsapi 缺失：`scripts/install_extras.sh download`
- rmse.csv 或 day6 png 缺失：`scripts/regression_minimal.sh`
- pip logging error：`scripts/fix_venv_pip.sh`

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
