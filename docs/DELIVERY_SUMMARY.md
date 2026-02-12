# DELIVERY SUMMARY（S1-S8 一页总览）

本页是复现执行总览。主线只用 `README.md`、`RUNBOOK.md`、本文件。

## S1 环境与依赖
- 目标：创建 CPU/GPU 环境并避免交叉污染
- 命令：
```bash
bash scripts/create_cpu_venv.sh
bash scripts/create_gpu_venv.sh
source scripts/env_gpu.sh
source configs/default.env
```
- 验收：`source scripts/env_gpu.sh` 输出包含 `CUDAExecutionProvider`
- 常见修复：`bash scripts/create_gpu_venv.sh --update`

## S2 CPU smoke
- 目标：验证包契约与 CPU 入口
- 命令：
```bash
scripts/run_cpu.sh -m pangu_weather_repro.smoke
```
- 验收：输出 `contracts smoke ok`

## S3 GPU smoke
- 目标：验证 GPU 推理入口可用
- 命令：
```bash
bash scripts/final_verify.sh
```
- 验收：Day3/Day5/Day6 子步骤通过

## S4 84h 推理
- 目标：完成短中期推理
- 命令：
```bash
scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --target-hours 84 --noarena --threads 1 --out-dir "$OUTPUT_ROOT/forecast_84h_$(date +%Y%m%d_%H%M%S)"
```
- 验收：目标目录内存在 `forecast_report.json`

## S5 360h 推理（稳态优先）
- 目标：分段+自动重试完成长链推理
- 命令：
```bash
bash scripts/run_360h_split.sh --auto-retry
```
- 验收：终端出现 `report long` 或 `[RETRY] success`

## S6 RMSE + Paper 图
- 目标：完成评估与论文图
- 命令：
```bash
bash scripts/final_verify.sh
```
- 产物：`artifacts/day5/rmse.csv`、`figures/day6/*.png`

## S7 产品图族 + Streamlit
- 目标：生成产品图并进行页面展示
- 命令：
```bash
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --impl auto --force
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
```
- 产物：`figures/product/*.png` + `figures/product/*.json`

## S8 最终验收
- 目标：仓库健康检查 + 主链闭环
- 命令：
```bash
bash scripts/verify_repo_health.sh
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```
- 验收：输出 `FINAL VERIFY PASS`

## 说明
- `scripts/` 是公开入口。
- `scripts/internal/` 与 `docs/_internal/` 是过程材料与内部脚本，不影响复现主链。
- 运行产物默认落在 `OUTPUT_ROOT`（通常 `/root/autodl-tmp/pangu-weather-repro/outputs`）。
