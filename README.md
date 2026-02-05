# Pangu-Weather Reproduction (UV + ONNXRuntime)

本仓库用于复现 Pangu-Weather 全球天气预报模型，强调可复现、可工程化与可审计。

## What You Can Reproduce
- Day4 多步 rollout（生成预测与评估包）
- Day5 RMSE 指标计算（z500）
- Day6 论文级示例图（GT/Pred/Error 三联图 + RMSE 曲线）
- Day7 可扩展评估与汇总（多变量、多 lead）
- Day8 论文口径对齐增强（lat-weighted RMSE + ACC）

## Repository Layout
```text
repo_root/
├── configs/                  # 环境变量与参数
│   ├── default.env           # 云端默认路径
│   └── default.yaml          # 变量顺序、层级等
├── scripts/                  # 数据与验证脚本
│   ├── 01_download_models.sh
│   ├── 03_download_era5_single.py
│   ├── 03_download_era5_pressure.py
│   ├── 04_preprocess_era5_to_npy.py
│   └── 05_validate_inputs.py
├── tools/                    # 推理/评估/可视化
│   ├── day4_rollout.py
│   ├── eval_rmse.py
│   ├── plot_fields.py
│   ├── plot_rmse_curve.py
│   ├── day7_metrics.py
│   └── day7_plot_summary.py
├── artifacts/                # 指标结果（小文件）
│   ├── day5/rmse.csv
│   └── day7/metrics_summary.csv
├── figures/                  # 示例图像
│   ├── day6/*.png
│   └── day7/summary_rmse.png
├── docs/                     # 结果说明
│   ├── day6_results.md
│   └── day7_results.md
├── README.md
├── RUNBOOK.md
├── pyproject.toml
└── uv.lock
```

## Environment
- 云端：
```bash
source configs/default.env
```
- 本地：
```bash
source configs/local.env
```
说明：`configs/local.env` 需你自行创建，参考 `configs/default.env`。

## Quickstart (10–15 min, Day4 → Day6 最小闭环，不跨天)
> 目标：跑通最小闭环并生成两张图。

### 1) 下载模型（Day1）
```bash
bash scripts/01_download_models.sh
```

### 2) 下载 ERA5（Day1）
```bash
uv run python scripts/03_download_era5_single.py --date 20230709 --hour 00
uv run python scripts/03_download_era5_pressure.py --date 20230709 --hour 00
uv run python scripts/03_download_era5_single.py --date 20230709 --hour 06
uv run python scripts/03_download_era5_pressure.py --date 20230709 --hour 06
```

### 3) ERA5 预处理（Day2）
```bash
uv run python scripts/04_preprocess_era5_to_npy.py --date 20230709 --hour 00
```

### 4) Rollout + 评估包（Day4，6h）
```bash
uv run python tools/day4_rollout.py --steps 6 --noarena --out-dir "$OUTPUT_ROOT/day4_rollout_06h"
```
产物：
- `$OUTPUT_ROOT/day4_rollout_06h/eval_z500.npz`
- `$OUTPUT_ROOT/day4_rollout_06h/eval_z500_meta.json`

### 5) RMSE（Day5）
```bash
uv run python tools/eval_rmse.py --pred "$OUTPUT_ROOT/day4_rollout_06h/eval_z500.npz" --var z500 --out artifacts/day5/rmse.csv
```

### 6) 论文级示例图（Day6）
```bash
uv run python tools/plot_fields.py --var z500 --lead 6
uv run python tools/plot_rmse_curve.py --var z500
```

产物：
- `figures/day6/field_z500_2023070900_t+006.png`
- `figures/day6/rmse_z500_2023070900.png`

## Day7 Quickstart (多变量、多 lead 汇总)
默认不跨天，仅 6h：
```bash
uv run python tools/day7_metrics.py --vars z500,t2m,u10 --leads 6 --out artifacts/day7/metrics_summary.csv --md docs/day7_results.md
uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric rmse_latw --out figures/day7/summary_rmse.png
```
如果需要 24h，请先下载 `20230710 00` 的 ERA5 single/pressure。

## Day8 Quickstart (lat-weighted RMSE + ACC)
```bash
uv run python tools/day7_metrics.py --vars z500,t2m,u10 --leads 6 --out artifacts/day7/metrics_summary.csv --md docs/day7_results.md
uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric rmse_latw --out figures/day7/summary_rmse.png
uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric acc_latw --out figures/day7/summary_acc.png
```

## Output Locations
- 大文件：`$OUTPUT_ROOT` 或 `$DATA_ROOT`
- 指标表：`artifacts/day5/rmse.csv`、`artifacts/day7/metrics_summary.csv`
- 示例图：`figures/day6/`、`figures/day7/summary_rmse.png`、`figures/day7/summary_acc.png`
- 结果说明：`docs/day6_results.md`、`docs/day7_results.md`

## Reproducibility Rules
- 统一使用 `source configs/default.env` 或 `configs/local.env`。
- 输出路径固定，评估包与图像均包含日期与 lead time。
- 绘图无随机性，运行参数一致可得到一致结果。

## Verification Checklist
- 模型存在：
```bash
ls -lh "$MODELS_ROOT" | grep pangu_weather_24.onnx
```
- Day4 评估包存在：
```bash
ls -lh "$OUTPUT_ROOT/day4_rollout_06h" | grep eval_z500
```
- Day5 RMSE 表存在：
```bash
head -n 3 artifacts/day5/rmse.csv
```
- Day7 汇总表存在：
```bash
head -n 5 artifacts/day7/metrics_summary.csv
```
- Day6/Day7 图片存在：
```bash
find figures/day6 -maxdepth 1 -name "*.png"
find figures/day7 -maxdepth 1 -name "*.png"
```

## Common Issues
- ERA5 队列拥堵：等 CDS Successful 后用 `wget` 下载到 `$ERA5_RAW_ROOT`。
- Day4 GPU OOM：使用 `--noarena` 或设置 `ORT_GPU_MEM_LIMIT_MB`。
- Day5/Day7 找不到 ERA5：补齐对应时次的 pressure/single 文件。

详细步骤与排错请阅读 `RUNBOOK.md`。
