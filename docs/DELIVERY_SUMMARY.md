# DELIVERY SUMMARY（阶段化复现交付）

中文说明：
- 目标是让复现人员只按阶段执行，不需要理解内部实现细节。
- 默认不覆盖产物，需覆盖时显式加 `--force`。

## S1 环境与依赖
- 目标：创建 CPU/GPU 环境，避免交叉污染。
- 命令：
```bash
bash scripts/create_cpu_venv.sh && bash scripts/create_gpu_venv.sh
source scripts/env_cpu.sh && source scripts/env_gpu.sh
```
- 产物：`.venv-cpu/`、`.venv-gpu/`
- 验收：`source scripts/env_gpu.sh` 输出 providers 含 `CUDAExecutionProvider`
- 失败修复：`bash scripts/install_gpu_deps.sh --force`

## S2 CPU Smoke
- 目标：验证 contracts 与包导入正常。
- 命令：
```bash
bash scripts/run_day8_cpu_smoke.sh
```
- 产物：终端输出 `contracts smoke ok`
- 验收：退出码 0
- 失败修复：`bash scripts/create_cpu_venv.sh --update`

## S3 GPU Smoke
- 目标：验证 ONNXRuntime GPU 推理入口。
- 命令：
```bash
bash scripts/run_day3_smoke_gpu.sh
```
- 产物：`$OUTPUT_ROOT/smoke_24h_report.json`
- 验收：`providers_used` 包含 `CUDAExecutionProvider`
- 失败修复：`bash scripts/install_gpu_deps.sh --force`

## S4 84h 推理
- 目标：完成 84h 预测链。
- 命令：
```bash
scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --target-hours 84 --noarena --threads 1 --out-dir "$OUTPUT_ROOT/forecast_84h_$(date +%Y%m%d_%H%M%S)"
```
- 产物：`forecast_report.json`
- 验收：报告存在且步骤完整
- 失败修复：减小内存限制或改用 split（见 S5）

## S5 360h 推理（split/resume）
- 目标：稳定完成长链推理，支持中断续跑。
- 命令：
```bash
bash scripts/run_360h_split.sh --auto-retry
```
- 产物：`forecast_360h_split_*_84h/forecast_report.json` 与 `*_276h/forecast_report.json`
- 验收：终端出现 `[RETRY] success` 或 `report long`
- 失败修复：`bash scripts/run_360h_split.sh --auto-retry --mem-series 12288,10240,8192,6144`

## S6 RMSE + Paper 图
- 目标：完成 Day5/Day6 评估与论文图。
- 命令：
```bash
bash scripts/run_day5_rmse.sh && bash scripts/run_day6_plots.sh
```
- 产物：`artifacts/day5/rmse.csv`、`figures/day6/*.png`
- 验收：文件存在且非空
- 失败修复：`source configs/default.env && scripts/run_gpu.sh scripts/04_preprocess_era5_to_npy.py --date 20230709 --hour 00`

## S7 产品图族 + Streamlit
- 目标：生成产品化图族并在页面查看。
- 命令：
```bash
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
```
- 产物：`figures/product/*.png`、`figures/product/*.json`
- 验收：`bash scripts/run_e_stage_verify.sh --force` 结果为 ok
- 失败修复：`bash scripts/install_extras.sh plots --force`

## S8 最终验收
- 目标：主链 + E 阶段全量检查。
- 命令：
```bash
bash scripts/verify_repo_health.sh
bash scripts/final_verify.sh --with-e-stage --e-stage-force
bash scripts/gen_report.sh
```
- 产物：`artifacts/day7/REPORT.md`、`artifacts/day7/E_STAGE_REPORT.md`
- 验收：终端出现 `FINAL VERIFY PASS`
- 失败修复：按脚本 `[NEXT]` 提示执行对应命令
