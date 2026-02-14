# Pangu-Weather Repro (Delivery Edition)

本仓库面向"阶段化可复现交付"。复现人员只看三份文档即可：
- `README.md`：最短执行路径
- `RUNBOOK.md`：S1-S8 详细步骤与排错
- `docs/DELIVERY_SUMMARY.md`：阶段目标、产物、验收矩阵

功能调用速查：
- `docs/FUNCTION_CALL_MANUAL_ZH.md`：按"功能 -> 命令 -> 实际意义"快速调用

## 一键核查（推荐）

SSH 断线安全的一键核查命令（推荐在 tmux 中运行）：
```bash
cd /root/projects/pangu-weather-repro-paper

# 方式 1: tmux（推荐，断线后可重连）
tmux new -s verify 'bash scripts/one_shot_verify.sh --yes'
# 断线后重连: tmux attach -t verify

# 方式 2: nohup（后台运行）
nohup bash scripts/one_shot_verify.sh --yes > verify.log 2>&1 &
tail -f verify.log
```

该脚本自动完成：环境预检 -> CPU/GPU 冒烟 -> ERA5 真值检查 -> RMSE 评估 -> 论文图 -> 产品图 -> E 阶段验收 -> manifest 生成。

## 最短复现路径（新机器推荐）
```bash
cd /root/projects/pangu-weather-repro-paper
bash scripts/create_cpu_venv.sh
bash scripts/create_gpu_venv.sh
source scripts/env_gpu.sh && source configs/default.env
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt
bash scripts/run_360h_split.sh --auto-retry
bash scripts/one_shot_verify.sh --yes
```

## 空白机数据准备（必须先完成）

### 推理输入（surface.npy + pressure.npy）
```bash
# 自动下载（非交互）
bash scripts/prepare_era5_inputs.sh --yes

# 手动放置（无外网时）
# 原始 nc: $ERA5_RAW_ROOT/era5_single_2023070900.nc + era5_pressure_2023070900.nc
# 预处理 npy: $PROCESSED_ROOT/surface.npy + pressure.npy
```

### 评估真值（Day5 RMSE 需要）
```bash
# 自动下载 RMSE 评估所需的 ERA5 真值 pressure 文件
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt

# 手动放置（无外网时，按 rollout 步长推导文件名）
# $ERA5_RAW_ROOT/era5_pressure_2023071000.nc  (init+24h)
# $ERA5_RAW_ROOT/era5_pressure_2023071006.nc  (init+30h)
```

## 官方入口（只用 `scripts/`）
- 环境：`create_cpu_venv.sh`、`create_gpu_venv.sh`、`env_cpu.sh`、`env_gpu.sh`
- 数据：`prepare_era5_inputs.sh`（支持 `--ensure-eval-gt` 下载评估真值）
- 运行：`run_cpu.sh`、`run_gpu.sh`、`run_360h_split.sh`、`run_product_all.sh`、`run_streamlit.sh`
- 验收：`one_shot_verify.sh`（一键核查）、`verify_repo_health.sh`（轻量健康检查）、`final_verify.sh`（传统验收）
- 依赖安装：`install_extras.sh`

`scripts/internal/` 与 `docs/_internal/` 仅用于过程治理和内部排障，不作为对外主流程。

## 阶段总览（S1-S8）
- S1 环境与依赖
- S2 CPU smoke
- S3 GPU smoke
- S4 84h 推理
- S5 360h 推理（split/resume/auto-retry）
- S6 RMSE + paper 图
- S7 产品图族 + Streamlit
- S8 最终验收

详细命令见 `RUNBOOK.md`。

## SSH 断线 / 重连指南

| 场景 | 操作 |
|------|------|
| tmux 断线 | `tmux attach -t verify` |
| nohup 运行中 | `tail -f verify.log` 或 `tail -f logs/one_shot_verify_*.log` |
| screen 断线 | `screen -r verify` |
| 查看最新日志 | `ls -lt logs/one_shot_verify_*.log \| head -1` |
| 检查是否还在运行 | `cat .one_shot_verify.lock && ps -p $(cat .one_shot_verify.lock)` |
| 强制重跑 | `bash scripts/one_shot_verify.sh --yes --force-kill` |

## 只跑单个阶段
```bash
# 只跑 Day5 RMSE
bash scripts/internal/run_day5_rmse.sh --force

# 只跑 Day6 出图
bash scripts/internal/run_day6_plots.sh --force

# 只跑产品图
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force

# 只跑 E 阶段
bash scripts/internal/run_e_stage_verify.sh --force

# 跳过已通过的阶段
bash scripts/one_shot_verify.sh --yes --skip-cpu-smoke --skip-gpu-smoke
```

## 产品图实现选择
`run_product_all.sh` 支持 `--impl`：
- `auto`：默认，优先稳定
- `native`：本仓库原生实现
- `blueprint`：蓝本适配实现

## 常见故障快速修复

| 故障 | 修复命令 |
|------|----------|
| `CUDAExecutionProvider` 缺失 | `bash scripts/create_gpu_venv.sh --update && source scripts/env_gpu.sh` |
| 绘图依赖缺失（matplotlib/scipy） | `bash scripts/install_extras.sh plots --force` |
| RMSE 依赖缺失（netCDF4） | `bash scripts/install_extras.sh rmse` |
| 缺少 ERA5 推理输入 | `bash scripts/prepare_era5_inputs.sh --yes` |
| 缺少 ERA5 评估真值 | `bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt` |
| 360h OOM | `bash scripts/run_360h_split.sh --auto-retry` |
| Streamlit 外网 503 | SSH 隧道 `http://127.0.0.1:8501` |
| 已有核查在运行 | `bash scripts/one_shot_verify.sh --force-kill --yes` |
| Python 环境不对 | 确保先 `source scripts/env_gpu.sh` |
| nohup 日志空白 | 使用 `one_shot_verify.sh`（已内置 PYTHONUNBUFFERED） |

## 清理与从头再来
```bash
# 查看占用
bash scripts/internal/cleanup_check.sh

# 预览清理（不实际删除）
bash scripts/internal/cleanup_autodl.sh --dry-run

# 执行清理
bash scripts/internal/cleanup_autodl.sh --force --keep-latest 2 --keep-days 3

# 完全从头再来（删除所有产物后重跑）
bash scripts/one_shot_verify.sh --yes --force
```

## 目录说明（复现视角）
- `pangu_weather_repro/`：核心代码
- `scripts/`：公开入口
- `tools/`：高级 CLI
- `configs/`：路径与环境配置
- `docs/`：对外交付文档
- `vendor/blueprint/`：蓝本镜像与适配基础
- `logs/`：核查日志（由 one_shot_verify.sh 生成）
- `artifacts/`：产物目录（rmse.csv、manifest.json、E_STAGE_REPORT.md）

运行产物默认写入 `OUTPUT_ROOT`（一般为 `/root/autodl-tmp/pangu-weather-repro/outputs`）。
