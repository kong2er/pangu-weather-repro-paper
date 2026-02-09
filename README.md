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

## Dual Envs (CPU/GPU 分离，避免依赖互相覆盖)
```bash
make env-cpu
make env-gpu
```
CPU 环境执行（CI/Day8）：`UV_VENV=.venv-cpu .venv-cpu/bin/python ...`
GPU 环境执行（Day3/4/7 推理）：`UV_VENV=.venv-gpu .venv-gpu/bin/python ...`

快速切换（推荐）：
```bash
source scripts/env_cpu.sh
source scripts/env_gpu.sh
```

## Day Plan (每天工作与意义)
- Day1: 环境搭建与 ERA5 API 连接，确认能下载单个时次数据与模型，保证数据源可达。
- Day2: ERA5 预处理与变量顺序校验，生成可用的 `surface/pressure` 输入。
- Day3: 模型加载与单次推理验证，确保 ONNXRuntime 正常且输出尺寸正确。
- Day4: 多步推理与评估包生成，形成 Day5/6/7 的统一输入。
- Day5: RMSE 指标计算，验证误差量级与评估流程可信。
- Day6: 可视化输出，生成论文级示例图与曲线。
- Day7: 多变量多 lead 汇总评估，形成可扩展指标表与汇总图。
- Day8: 代码结构与 CI 收官，补 smoke/health-check，确保开箱即用。

## Fresh Clone (开箱即用)
```bash
uv sync
make smoke
```

## Quickstart (离线 smoke，< 1 min)
> 目标：无需模型/ERA5/密钥，在 CPU 上验证“预处理 → 张量组装 → feed dict”契约。

```bash
uv sync
make smoke
```

## Quickstart (GPU, Stable Minimal)
```bash
make env-gpu
scripts/fix_venv_pip.sh
scripts/install_gpu_deps.sh
scripts/install_extras.sh rmse
scripts/install_extras.sh plots
scripts/run_day3_smoke_gpu.sh
scripts/run_day5_rmse.sh
scripts/run_day6_plots.sh
scripts/regression_minimal.sh
```

## Quickstart (CPU)
```bash
make env-cpu
source scripts/env_cpu.sh
python -m pangu_weather_repro.smoke
```

## Smoke Types
- CI smoke（无数据、无 GPU）：`uv sync` → `make smoke` → `uv run pytest -q`
- Runtime smoke（有数据/模型）：`source configs/default.env` → `make smoke-runtime`

## Repo Health Check
```bash
uv run python tools/check_repo_health.py
```

## 功能说明（中文）
Day1：配置 ERA5 API 与模型下载，确保数据源与权重可达，是后续全部流程的前置条件。
Day2：将 ERA5 转为模型输入并校验变量顺序/形状，保证输入契约正确。
Day3：ONNX 模型单次推理 smoke，验证运行环境与输出尺寸正确。
Day4：多步推理与评估包生成，为 Day5–Day7 提供统一输入。
Day5：RMSE 指标计算，用于评估误差量级与正确性。
Day6：生成论文级可视化图，验证绘图流程与输出质量。
Day7：多变量多 lead 汇总，形成可扩展指标表与汇总图。
Day8：结构与 CI 收官，确保仓库开箱即用与可持续维护。

CI smoke 作用：不依赖数据/GPU，验证“可安装 + 可 import + CLI help 可跑 + 基础测试”。
Runtime smoke 作用：在有模型/数据时验证推理链路可运行。

## 单独功能调用（含中文说明）
CPU-only（CI/Day8/离线）：
```bash
source scripts/env_cpu.sh
python -m pangu_weather_repro.smoke
```

GPU 推理（Day3/4/7）：
```bash
source configs/default.env
source scripts/env_gpu.sh
python tools/day4_rollout.py --steps 24,6 --noarena --out-dir "$OUTPUT_ROOT/day4_rollout_30h"
```

只跑 RMSE（Day5）：
```bash
source scripts/env_gpu.sh
python tools/eval_rmse.py --pred "$OUTPUT_ROOT/day4_rollout_06h/eval_z500.npz" --var z500 --out artifacts/day5/rmse.csv
```

只跑 Day7 指标：
```bash
source configs/default.env
source scripts/env_gpu.sh
python tools/day7_metrics.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500,t2m,u10 --leads 24 --out artifacts/day7/metrics_summary.csv --md docs/day7_results.md
```

## GPU 环境常见提示（可忽略/快速修复）
如果看到 “pip 依赖冲突提示（missing cartopy/xarray/…）”，这是提醒未装齐可选依赖，不影响当前命令执行。

若出现 “pip logging error：找不到 .venv-gpu/bin/pip”，可用以下单行修复（不影响代码）：
```bash
source scripts/env_gpu.sh && python -m ensurepip --upgrade && python -m pip install -U pip && ln -sf .venv-gpu/bin/python .venv-gpu/bin/pip
```

## Troubleshooting
- 报错 `ModuleNotFoundError: netCDF4`：`scripts/install_extras.sh rmse`
- 报错 `ModuleNotFoundError: cdsapi`：`scripts/install_extras.sh download`
- 报错 `ModuleNotFoundError: matplotlib/cartopy`：`scripts/install_extras.sh plots`
- 报错 `CUDAExecutionProvider` 不可用 / `libcublasLt.so.12`：`scripts/install_gpu_deps.sh` 后 `source scripts/env_gpu.sh`
- 报错 `lead not in available leads`：30h rollout 仅支持 lead 24/30，或改用 6h rollout
- 报错 `missing gt_paths`：使用 `--rollout-dir $OUTPUT_ROOT/day4_rollout_30h` 或补齐 ERA5
- 报错 `pip logging error`：`scripts/fix_venv_pip.sh`
- 报错导入路径：用 `scripts/run_gpu.sh <script>` 代替直接 `python`

## FAQ
Q: 为什么 smoke 不加载 ONNX 或权重？
A: 目标是快速校验“预处理 → 输入张量组装 → feed dict”的契约，避免 shape/rank/变量顺序问题，因此仅做 contracts 校验。

Q: smoke 为什么这么快？
A: 使用广播零张量做形状验证，不分配完整 721x1440 大数组，保证 < 60s。

Q: CI 会下载 ERA5 或模型吗？
A: 不会。CI 仅跑 smoke/pytest/health-check 的 CPU-only 离线检查，不访问 ERA5/CDS，也不需要任何密钥。

## Full Run (10–15 min, Day4 → Day6 最小闭环，不跨天)
> 目标：跑通最小闭环并生成两张图（需要模型权重 + ERA5）。
依赖说明：
- ERA5：需要可用的 CDS API key（`~/.cdsapirc`），下载目录为 `$ERA5_RAW_ROOT`。
- 权重：通过 `scripts/01_download_models.sh` 下载到 `$MODELS_ROOT`。
- 约定目录：`$PROCESSED_ROOT`、`$OUTPUT_ROOT`（见 `configs/default.env`）。

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
如果需要完整 360h 预测（用于验证与长时效评估），请使用 Makefile 目标 `make rollout-360h`。

## Day8 Quickstart (lat-weighted RMSE + ACC)
```bash
uv run python tools/day7_metrics.py --vars z500,t2m,u10 --leads 6 --out artifacts/day7/metrics_summary.csv --md docs/day7_results.md
uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric rmse_latw --out figures/day7/summary_rmse.png
uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric acc_latw --out figures/day7/summary_acc.png
```

## Makefile Shortcuts
```bash
make env
make env-cpu
make env-gpu
make models
make era5-0900
make era5-0906
make preprocess
make rollout-6h
make rollout-30h
make rollout-360h
make day7
make day8
make smoke
make smoke-runtime
make check
```

## Output Locations
- 大文件：`$OUTPUT_ROOT`
- 指标表：`artifacts/day5/rmse.csv`、`artifacts/day7/metrics_summary.csv`
- 示例图：`figures/day6/`、`figures/day7/summary_rmse.png`、`figures/day7/summary_acc.png`
- 结果说明：`docs/day6_results.md`、`docs/day7_results.md`

## Contract (代码化约束)
- 入口文件：`pangu_weather_repro/contracts.py`
- Surface 变量顺序：`msl, u10, v10, t2m`
- Upper-air 变量顺序：`z, q, t, u, v`
- Pressure levels：`[1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50]`
- Grid：`721 x 1440`
- 坐标范围：lat `[90, -90]`，lon `[0, 359.75]`，分辨率 `0.25°`
- dtype：`float32`
- 允许输入 shape：
  - surface: `(4, 1, 721, 1440)` 或 `(4, 721, 1440)`
  - upper: `(5, 1, 13, 721, 1440)` 或 `(5, 13, 721, 1440)`
- ONNX feed keys（本仓库约定）：`input`（upper）与 `input_surface`（surface）

## 实现对齐说明（reference ↔ 本仓库）
> 说明：以下行级对齐基于本地 clone 的 `kong2er/pangu`（路径 `/tmp/pangu`），对应文件与行号已记录，后续若 reference 更新请同步校验。

- Reference: `pangu/pangu.py`（/tmp/pangu/pangu/pangu.py）
  - 变量顺序：`surf_vars = ['msl','u10','v10','t2m']` 与 `upper_vars = ['z','q','t','u','v']`
    - 对应：`pangu_weather_repro/contracts.py` 的 `SURFACE_VARS` / `UPPER_VARS`
    - 行号：`/tmp/pangu/pangu/pangu.py:116-117`
  - Pressure levels：`[1000, 925, ..., 50]`
    - 对应：`pangu_weather_repro/contracts.py` 的 `PRESSURE_LEVELS`
    - 行号：`/tmp/pangu/pangu/pangu.py:56`
  - Grid / 坐标范围：`lat=90..-90 (721)`，`lon=0..359.75 (1440)`
    - 对应：`pangu_weather_repro/contracts.py` 的 `LAT_RANGE/LON_RANGE/LAT_SIZE/LON_SIZE`
    - 行号：`/tmp/pangu/pangu/pangu.py:54-55`
  - ONNX feed keys：`session.run(..., {'input': input, 'input_surface': input_surface})`
    - 对应：`pangu_weather_repro/contracts.py:build_feed_dict`
    - 行号：`/tmp/pangu/pangu/pangu.py:167`
  - 输入 dtype：`astype('f4')`
    - 对应：`pangu_weather_repro/contracts.py` 的 `DTYPE=float32`
    - 行号：`/tmp/pangu/pangu/pangu.py:107-108`
  - `gh` 兼容：若 `gh` 存在且 `z` 不存在，则 `z = gh * 9.80665`
    - 对应：`scripts/04_preprocess_era5_to_npy.py` 直接使用 `z`
    - 行号：`/tmp/pangu/pangu/pangu.py:105-106`

- Reference: `scripts/era5_to_pangu_input.py`（/tmp/pangu/scripts/era5_to_pangu_input.py）
  - ERA5 压力层顺序：`PL_LEVELS` 与 `pangu.py` 一致
    - 对应：`configs/default.yaml` + `pangu_weather_repro/contracts.py`
    - 行号：`/tmp/pangu/scripts/era5_to_pangu_input.py:8,45`
  - ERA5 单层变量：`msl, u10, v10, t2m`（同时包含 `u100/v100`）
    - 对应：`scripts/04_preprocess_era5_to_npy.py` 选取 `msl,u10,v10,t2m`
    - 行号：`/tmp/pangu/scripts/era5_to_pangu_input.py:22-63`

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
- ContractError：检查 `surface/upper` 的 rank 与变量顺序，运行 `python -m pangu_weather_repro.smoke` 快速定位。

详细步骤与排错请阅读 `RUNBOOK.md`。
