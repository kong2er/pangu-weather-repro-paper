# DELIVERY SUMMARY（S1-S8 阶段总览）

本页用于快速审阅“每阶段做什么、产物在哪里、如何判定通过”。

| 阶段 | 目标 | 命令 | 关键产物 | 通过标准 |
|---|---|---|---|---|
| S1 | 创建 CPU/GPU 环境 | `bash scripts/create_cpu_venv.sh`<br>`bash scripts/create_gpu_venv.sh`<br>`source scripts/env_gpu.sh` | `.venv-cpu` / `.venv-gpu` | `env_gpu.sh` 输出包含 `CUDAExecutionProvider` |
| S2 | CPU smoke | `scripts/run_cpu.sh -m pangu_weather_repro.smoke` | 终端 smoke 输出 | `contracts smoke ok` |
| S3 | GPU smoke | `bash scripts/final_verify.sh` | `smoke_24h_report.json` | Day3/Day5/Day6 子步骤通过 |
| S4 | 84h 推理 | `scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --target-hours 84 --noarena --threads 1 --out-dir "$OUTPUT_ROOT/forecast_84h_$(date +%Y%m%d_%H%M%S)"` | `forecast_report.json` | 报告生成且步骤完整 |
| S5 | 360h 推理 | `bash scripts/run_360h_split.sh --auto-retry` | `forecast_360h_split_*` 报告 | 终端出现 `report long` 或 `[RETRY] success` |
| S6 | RMSE + paper 图 | `bash scripts/final_verify.sh` | `artifacts/day5/rmse.csv`<br>`figures/day6/*.png` | 文件存在且非空 |
| S7 | 产品图族 + Streamlit | `bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --impl auto --force`<br>`bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501` | `figures/product/*.png`<br>`figures/product/*.json` | 图生成成功；页面可访问 |
| S8 | 最终验收 | `bash scripts/verify_repo_health.sh`<br>`bash scripts/final_verify.sh --with-e-stage --e-stage-force` | `artifacts/day7/REPORT.md`<br>`artifacts/day7/E_STAGE_REPORT.md` | `FINAL VERIFY PASS` |

## 快速排错
- GPU provider 缺失：`bash scripts/create_gpu_venv.sh --update && source scripts/env_gpu.sh`
- OOM：`bash scripts/run_360h_split.sh --auto-retry`
- 绘图依赖缺失：`bash scripts/install_extras.sh plots --force`
- Streamlit 503：使用 SSH 隧道访问 `http://127.0.0.1:8501`

## 备注
- 对外只需要 `scripts/` 顶层入口。
- `scripts/internal/` 和 `docs/_internal/` 为内部流程材料，不影响主线复现。
