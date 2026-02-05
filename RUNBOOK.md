# RUNBOOK – Pangu-Weather Reproduction

本手册是可复现操作指南。目标是让你明确：做到哪一步、为什么做、产物是什么、如何验证、失败时怎么修。

## Progress Checklist
- Day1: 下载 ERA5 raw 与模型文件
- Day2: ERA5 → NumPy 预处理完成
- Day3: ONNX 推理 smoke 通过
- Day4: 多步 rollout 与 eval 元信息生成
- Day5: RMSE 指标生成
- Day6: 论文级示例图生成
- Day7: 多变量多 lead 汇总生成
- Day8: lat-weighted RMSE + ACC 对齐增强

---

## Day1: 环境、模型与 ERA5 下载
- Goal: 准备运行环境与基础输入数据。
- Why: 模型文件与 ERA5 是全流程最基础依赖。
- Commands:
```bash
uv venv --python 3.10
uv sync
source configs/default.env
bash scripts/01_download_models.sh
uv run python scripts/03_download_era5_single.py --date 20230709 --hour 00
uv run python scripts/03_download_era5_pressure.py --date 20230709 --hour 00
uv run python scripts/03_download_era5_single.py --date 20230709 --hour 06
uv run python scripts/03_download_era5_pressure.py --date 20230709 --hour 06
```
- Outputs:
- `$MODELS_ROOT/pangu_weather_1.onnx`
- `$MODELS_ROOT/pangu_weather_3.onnx`
- `$MODELS_ROOT/pangu_weather_6.onnx`
- `$MODELS_ROOT/pangu_weather_24.onnx`
- `$ERA5_RAW_ROOT/era5_single_2023070900.nc`
- `$ERA5_RAW_ROOT/era5_pressure_2023070900.nc`
- `$ERA5_RAW_ROOT/era5_single_2023070906.nc`
- `$ERA5_RAW_ROOT/era5_pressure_2023070906.nc`
- Verify:
```bash
ls -lh "$MODELS_ROOT" | grep pangu_weather_24.onnx
ls -lh "$ERA5_RAW_ROOT" | grep 2023070900
ls -lh "$ERA5_RAW_ROOT" | grep 2023070906
```
- If it fails:
- `cdsapi` 认证失败: 重新配置 `~/.cdsapirc` 并执行 `uv run python scripts/cds_smoke_t2m.py`。
- 下载卡在队列: 等 CDS 网站 `Successful` 后用下载链接 `wget` 到 `$ERA5_RAW_ROOT`。

---

## Day2: ERA5 → NumPy 预处理
- Goal: 将 ERA5 NetCDF 转为模型输入 NumPy。
- Why: ONNX 模型只接受固定顺序与形状的数组输入。
- Commands:
```bash
source configs/default.env
uv run python scripts/04_preprocess_era5_to_npy.py --date 20230709 --hour 00
uv run python scripts/05_validate_inputs.py
```
- Outputs:
- `$PROCESSED_ROOT/surface.npy`
- `$PROCESSED_ROOT/pressure.npy`
- Verify:
```bash
python - <<'PY'
import numpy as np, os
root=os.environ.get('PROCESSED_ROOT')
print(np.load(os.path.join(root,'surface.npy')).shape)
print(np.load(os.path.join(root,'pressure.npy')).shape)
PY
```
- If it fails:
- `FileNotFoundError`: 先完成 Day1 下载。
- `NaN` 或 shape 不一致: 重新运行 `scripts/04_preprocess_era5_to_npy.py`。

---

## Day3: ONNX 推理 Smoke
- Goal: 验证模型在 GPU/CPU 上可运行。
- Why: 确保 Day4 rollout 前运行环境正常。
- Commands:
```bash
source configs/default.env
uv run python tools/run_smoke_gpu_noarena.py --step 24
```
- Outputs:
- 终端输出包含 providers 与耗时信息。
- Verify:
```bash
uv run python tools/run_smoke_gpu_noarena.py --step 24 | head -n 5
```
- If it fails:
- GPU OOM: 使用 `--force-cpu` 或设置 `ORT_GPU_MEM_LIMIT_MB`。
- ORT 缺少 CUDA: 检查 `LD_LIBRARY_PATH` 是否已由 `configs/default.env` 设置。

---

## Day4: 多步 Rollout + 评估包
- Goal: 多步预测并导出评估包。
- Why: Day5 的 RMSE 与 Day6/Day7/Day8 的可视化都依赖评估包。
- Commands (不跨天，建议新手):
```bash
source configs/default.env
uv run python tools/day4_rollout.py --steps 6 --noarena --out-dir "$OUTPUT_ROOT/day4_rollout_06h"
```
- Commands (可选跨天 24h+6h):
```bash
uv run python tools/day4_rollout.py --steps 24,6 --noarena --out-dir "$OUTPUT_ROOT/day4_rollout_30h"
```
- Outputs:
- `$OUTPUT_ROOT/day4_rollout_06h/rollout_report.json`
- `$OUTPUT_ROOT/day4_rollout_06h/eval_z500.npz`
- `$OUTPUT_ROOT/day4_rollout_06h/eval_z500_meta.json`
- Verify:
```bash
ls -lh "$OUTPUT_ROOT/day4_rollout_06h" | grep eval_z500
```
- If it fails:
- GPU OOM: 添加 `--noarena` 或 `ORT_GPU_MEM_LIMIT_MB=12000`。
- 输出目录为空: 确认 `--out-dir` 指向 `$OUTPUT_ROOT`。
- 24h/30h 跨天: 需要 Day5/Day7/Day8 的 ERA5 `20230710 00/06` 真值文件。

---

## Day5: RMSE 评估（z500）
- Goal: 计算 z500 的 RMSE 指标。
- Why: 量化预测误差，为 Day6 曲线与论文指标提供基础。
- Commands (对应 6h):
```bash
source configs/default.env
uv run python tools/eval_rmse.py --pred "$OUTPUT_ROOT/day4_rollout_06h/eval_z500.npz" --var z500 --out artifacts/day5/rmse.csv
```
- Outputs:
- `artifacts/day5/rmse.csv`
- Verify:
```bash
head -n 3 artifacts/day5/rmse.csv
```
- If it fails:
- `FileNotFoundError eval_z500`: 先完成 Day4。
- `FileNotFoundError era5_pressure_2023070906`: 下载对应 ERA5 pressure 文件。

---

## Day6: 可视化（论文级示例图）
- Goal: 生成可复现实验图像。
- Why: 直观展示预测质量与误差随 lead time 变化。
- Commands (对应 6h):
```bash
source configs/default.env
uv run python tools/plot_fields.py --var z500 --lead 6
uv run python tools/plot_rmse_curve.py --var z500
```
- Outputs:
- `figures/day6/field_z500_2023070900_t+006.png`
- `figures/day6/rmse_z500_2023070900.png`
- Verify:
```bash
find figures/day6 -maxdepth 1 -name "*.png"
```
- Verify (inputs chosen by script):
```bash
uv run python tools/plot_fields.py --var z500 --lead 6 | head -n 6
```
- If it fails:
- `meta not found`: 先完成 Day4。
- `rmse.csv not found`: 先完成 Day5。

---

## Day7: 多变量多 lead 汇总
- Goal: 批量计算多变量、多 lead 的 RMSE 并汇总。
- Why: 从单变量示例升级为可扩展的评估与汇总，便于对外汇报。
- Commands (默认不跨天):
```bash
source configs/default.env
uv run python tools/day7_metrics.py --vars z500,t2m,u10 --leads 6 --out artifacts/day7/metrics_summary.csv --md docs/day7_results.md
uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric rmse_latw --out figures/day7/summary_rmse.png
```
- Outputs:
- `artifacts/day7/metrics_summary.csv`
- `docs/day7_results.md`
- `figures/day7/summary_rmse.png`
- Verify:
```bash
ls -lh artifacts/day7/metrics_summary.csv
head -n 5 artifacts/day7/metrics_summary.csv
ls -lh figures/day7/summary_rmse.png
```
- Verify (inputs chosen by script):
```bash
uv run python tools/day7_metrics.py --vars z500,t2m,u10 --leads 6 --out artifacts/day7/metrics_summary.csv --md docs/day7_results.md | head -n 6
```
- If it fails:
- `meta not found`: 先完成 Day4。
- `missing rollout outputs`: lead 必须在 Day4 steps 范围内，或重新跑 rollout。
- `FileNotFoundError era5_single/pressure`: 补齐对应 ERA5 时次。

---

## Day8: 论文口径对齐增强（lat-weighted RMSE + ACC）
- Goal: 对齐论文常用口径（纬度加权 RMSE 与 ACC）。
- Why: 更符合论文常用评估指标，便于对比与汇报。
- Commands (默认不跨天):
```bash
source configs/default.env
uv run python tools/day7_metrics.py --vars z500,t2m,u10 --leads 6 --out artifacts/day7/metrics_summary.csv --md docs/day7_results.md
uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric rmse_latw --out figures/day7/summary_rmse.png
uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric acc_latw --out figures/day7/summary_acc.png
```
- Outputs:
- `artifacts/day7/metrics_summary.csv`
- `figures/day7/summary_rmse.png`
- `figures/day7/summary_acc.png`
- Verify:
```bash
ls -lh artifacts/day7/metrics_summary.csv
head -n 5 artifacts/day7/metrics_summary.csv
ls -lh figures/day7/summary_rmse.png
ls -lh figures/day7/summary_acc.png
```
- If it fails:
- `latitude not found`: 确保 ERA5 文件包含 `latitude` 变量。
- `acc` 为 NaN: 检查 GT 是否全 NaN 或常数场。

---

## Notes
- 云端统一使用 `source configs/default.env`。
- 本地使用 `source configs/local.env`，仅说明不提交。
- 大文件写入 `$OUTPUT_ROOT`，示例图写入 `figures/`。
