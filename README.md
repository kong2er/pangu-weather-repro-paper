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
- 1–84h 逐小时：`tools/run_forecast.py --strategy pangu_ref --mode short --short-step 1 --target-hours 84`
- 84–360h 迭代：`tools/run_forecast.py --strategy pangu_ref --mode full --short-step 1 --long-step 24 --target-hours 360`
- 仅计划不跑：`tools/run_forecast.py --strategy pangu_ref --dry-run --mode full --target-hours 360`
- `kong2er_ref`：与 `pangu_ref` 等价（为蓝本对齐保留显式命名）

示例（GPU 环境）：
```bash
scripts/run_gpu.sh tools/run_forecast.py --mode short --short-step 1 --target-hours 24
scripts/run_gpu.sh tools/run_forecast.py --strategy pangu_ref --mode full --short-step 1 --long-step 24 --target-hours 360 --dry-run
```
如遇显存不足（OOM），可加：
`--noarena` 或 `--gpu-mem-limit-mb 4096`。
推荐 360h 稳定跑法（分段）：
```bash
scripts/run_360h_split.sh
```
更稳（限制显存上限，避免碎片化）：
```bash
scripts/run_360h_split.sh --gpu-mem-limit-mb 4096
```
断连/失败后可续跑（不会覆盖）：
```bash
scripts/run_360h_split.sh --resume-from /root/autodl-tmp/pangu-weather-repro/outputs/forecast_360h_split_YYYYMMDD_HHMMSS
```
自动重试（逐步降低显存上限，适合多次 OOM 环境）：
```bash
scripts/run_360h_split.sh --auto-retry
```

## 论文级图输出
```bash
scripts/run_gpu.sh tools/plot_paper_bundle.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --var z500
```
可选参数：`--no-map`（不画底图）、`--cmap`、`--vmin/--vmax`、`--dpi`。若未安装 cartopy，会自动回退到无地图绘制。

## Region 扩展（可插拔数据适配层）
```bash
scripts/run_cpu.sh tools/region_demo.py --lat-min 28 --lat-max 35 --lon-min 118 --lon-max 123
```
若需要回填到全局网格（用于模型输入形状对齐）：
```bash
scripts/run_cpu.sh tools/region_demo.py --lat-min 28 --lat-max 35 --lon-min 118 --lon-max 123 --pad-to-global --fill-value 0.0
```
Region 元数据（示例输出）：
- `outputs/region_demo/region_meta.json`（包含裁剪范围、切片索引、形状、回填信息）

## Troubleshooting（常见错误 → 命令）
- CPU venv 缺失：`scripts/create_cpu_venv.sh`
- CPU 更新：`scripts/create_cpu_venv.sh --update`
- GPU venv 缺失：`scripts/create_gpu_venv.sh`
- GPU provider 缺失 / libcublasLt 缺失：`scripts/install_gpu_deps.sh && source scripts/env_gpu.sh`
- 模型下载失败（网络超时）：
```bash
scripts/01_download_models.sh --no-download
```
或使用 Google Drive 直链（默认无需 gdown，脚本内置 curl/wget/requests 回退）：  
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

## E1 Streamlit 骨架（可选）
安装：
```bash
bash scripts/install_extras.sh streamlit
```
启动：
```bash
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
```
说明：
- 页面为骨架：`Home / Forecast / Plots`
- 默认仅读取环境与目录信息，不改动现有产物

## E2 产品图族（可选）
生成产品图（默认不覆盖，需覆盖请加 `--force`）：
```bash
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500,t2m,u10,v10,msl --hours 24,30
```
区域产品图（示例：华东范围）：
```bash
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500,u10 --hours 24,30 --kinds fill,vector,msl_wind --extent 95,145,10,50 --force
```
一键生成完整图族（fill + diff + vector + wind_speed + msl_wind）：
```bash
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force
```
产物：
- `figures/product/product_*.png`
- `figures/product/product_*.json`
说明：
- 与 `plot_paper_bundle.py` 并行存在，不替代论文图流程
- `Plots` 页面会自动列出 `figures/product` 下文件
- 可选差值图（pred-ref，z500）：
```bash
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500 --hours 24,30 --kinds fill,diff --force
```
- `diff` 会优先使用 `eval_z500.npz` 内置 `gt_z500`；若缺失则自动回退读取 `eval_z500_meta.json` 的 `gt_paths`（无需重跑 Day4）
- 可选风场图（uv10 矢量）：
```bash
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars u10 --hours 24,30 --kinds vector --force
```
- 可选风速图（由 uv10 合成）：
```bash
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars u10 --hours 24,30 --kinds wind_speed --force
```
- 可选业务组合图（msl + uv10）：
```bash
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars u10 --hours 24,30 --kinds msl_wind --force
```
- 开启地理底图（可选）：
```bash
scripts/run_gpu.sh tools/plot_product_bundle.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500 --hours 24 --with-geo --geo-assets-dir assets/geo --extent 95,145,10,50 --force
```
- 无 `cartopy/scipy` 或无地理资源时会自动回退到普通绘图，不会中断流程
- 地理资源放置说明见：`assets/geo/README.md`
- 建议安装绘图扩展（含 `scipy`，提升地理绘图稳定性）：
```bash
bash scripts/install_extras.sh plots --force
```

## G 阶段推荐流程（蓝本对齐）
建议按以下顺序执行（单行可复制）：
```bash
source configs/default.env && source scripts/env_gpu.sh && bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force
```
```bash
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500,u10 --hours 24,30 --kinds fill,vector,wind_speed,msl_wind --style-profile standard --extent 95,145,10,50 --force
```
```bash
bash scripts/run_e_stage_verify.sh --force && sed -n '1,200p' artifacts/day7/E_STAGE_REPORT.md
```
说明：
- 第一条用于一键产出完整图族（含 wind_speed）。
- 第二条用于区域化业务图（含 style/extent）。
- 第三条用于生成并核查 E 阶段报告。

## 收官验收清单（建议逐条勾选）
0. 仓库轻量健康检查：`bash scripts/verify_repo_health.sh`
1. CPU 烟雾测试通过：`scripts/run_cpu.sh -m pangu_weather_repro.smoke`
2. GPU 最小链路通过：`scripts/regression_minimal.sh`
3. 360h 分段推理通过：`scripts/run_360h_split.sh --auto-retry`
4. 论文图输出生成：`figures/paper/*.png` + `figures/paper/*.json`
5. Region 适配 demo 通过：`tools/region_demo.py` 产物存在
6. 报告已更新：`artifacts/day7/REPORT.md`
7. 推理对齐记录：`artifacts/day7/alignment_experiments.md`

## 交付注意事项（重要）
1. 默认不覆盖产物，需覆盖请显式加 `--force`
2. 不提交 `.venv-*`（已在 `.gitignore`）
3. 模型下载建议优先用 `scripts/01_download_models.sh --source gdrive`
