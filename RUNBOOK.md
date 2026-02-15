# RUNBOOK (Stage-by-Stage Reproduction)

本手册给复现人员使用。按 S1-S8 顺序执行即可。

> **推荐**: 如果只想一键跑通全流程，直接用 `bash scripts/one_shot_verify.sh --yes`（见下方"一键核查"小节）。

## S0 预设
```bash
cd /root/projects/pangu-weather-repro-paper
source configs/default.env

# 确保 uv 已安装（本项目唯一包管理器）
uv --version || { curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc; }
```

## S1 环境与依赖

> **前置要求**：uv >= 0.4 已安装（见 S0）。所有虚拟环境创建和依赖安装均通过 uv 完成。

CPU 环境：
```bash
bash scripts/create_cpu_venv.sh
source scripts/env_cpu.sh
```

GPU 环境：
```bash
bash scripts/create_gpu_venv.sh
source scripts/env_gpu.sh
```

可选依赖：
```bash
bash scripts/install_extras.sh rmse        # netCDF4, cftime（Day5 RMSE 必需）
bash scripts/install_extras.sh plots --force  # matplotlib, cartopy, scipy（Day6/产品图必需）
bash scripts/install_extras.sh streamlit    # Streamlit 页面
```

阶段验收：
```bash
bash scripts/verify_repo_health.sh
```

## S2 CPU smoke
```bash
bash scripts/run_cpu.sh -m pangu_weather_repro.smoke
```
通过标准：输出 `contracts smoke ok`。

## S3 GPU smoke

### 准备 ERA5 输入
首次机器必须执行数据准备：
```bash
# 交互模式（会中文询问）
bash scripts/prepare_era5_inputs.sh

# 非交互模式（推荐 SSH 不稳定时使用）
bash scripts/prepare_era5_inputs.sh --yes

# 同时准备评估真值（推荐，避免 Day5 缺文件）
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt
```

如果 `~/.cdsapirc` 缺失且外网不可达，手工放置后再执行：
- 推理输入:
  - `$ERA5_RAW_ROOT/era5_single_2023070900.nc`
  - `$ERA5_RAW_ROOT/era5_pressure_2023070900.nc`
- 或预处理 npy:
  - `$PROCESSED_ROOT/surface.npy`
  - `$PROCESSED_ROOT/pressure.npy`
- 评估真值（Day5 需要）:
  - `$ERA5_RAW_ROOT/era5_pressure_2023071000.nc`（init+24h）
  - `$ERA5_RAW_ROOT/era5_pressure_2023071006.nc`（init+30h）

### 运行 GPU smoke
```bash
bash scripts/internal/run_day3_smoke_gpu.sh
```
通过标准：生成 `$OUTPUT_ROOT/smoke_24h_report.json`。

## S4 84h 推理
```bash
scripts/run_gpu.sh tools/run_forecast.py \
  --strategy kong2er_ref \
  --mode short \
  --target-hours 84 \
  --noarena --threads 1 \
  --out-dir "$OUTPUT_ROOT/forecast_84h_$(date +%Y%m%d_%H%M%S)"
```
通过标准：目标输出目录含 `forecast_report.json`。

## S5 360h 推理（稳态）
```bash
bash scripts/run_360h_split.sh --auto-retry
```
说明：自动分段与自动降载重试，优先保证跑通。

**SSH 断线保护**: 推荐在 tmux/screen 中运行长推理：
```bash
tmux new -s forecast 'bash scripts/run_360h_split.sh --auto-retry'
# 断线后: tmux attach -t forecast
```

## S6 RMSE + Paper 图

### 一键（推荐）
```bash
# 先确保评估真值存在
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt

# 再跑 RMSE + 出图
bash scripts/internal/run_day5_rmse.sh --force
bash scripts/internal/run_day6_plots.sh --force
```

### 如果 Day5 RMSE 报缺少真值文件
```
[WARN] 缺少 ERA5 真值文件:
  - /root/autodl-tmp/.../era5_pressure_2023071000.nc
```
**原因**: `prepare_era5_inputs.sh` 在 processed npy 存在时会跳过 raw nc 下载，但 Day5 RMSE 需要这些真值 nc 文件。

**修复**:
```bash
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt
# 然后重跑 RMSE
bash scripts/internal/run_day5_rmse.sh --force
```

## S7 产品图族 + Streamlit
产品图（默认稳定实现）：
```bash
bash scripts/run_product_all.sh \
  --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" \
  --hours 24,30 \
  --impl auto \
  --force
```

蓝本对齐实现：
```bash
bash scripts/run_product_all.sh \
  --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" \
  --hours 24,30 \
  --impl blueprint \
  --force
```

启动页面：
```bash
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
```

## S8 最终验收

### 方式 1: 一键核查（推荐）
```bash
bash scripts/one_shot_verify.sh --yes
```
功能包含：环境预检、CPU/GPU 冒烟、评估真值检查、RMSE、出图、产品图、E 阶段、manifest 生成。
通过标准：输出 `FINAL VERIFY PASS`。

### 方式 2: 传统验收
```bash
bash scripts/verify_repo_health.sh
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```

## 一键核查详细说明

`scripts/one_shot_verify.sh` 是为 AutoDL/容器/SSH 不稳定场景设计的一键核查脚本。

### 特性
- **SSH 断线安全**: 推荐 tmux/nohup 运行，脚本启动时打印断线重连方法
- **统一日志**: 所有阶段写入 `logs/one_shot_verify_<timestamp>.log`，Python 输出强制 unbuffered
- **并发保护**: lockfile 机制防止重复启动，支持 `--force-kill` 强制接管
- **产物校验**: 每阶段结束检查文件存在且非空
- **非交互**: `--yes` 全程不弹交互确认
- **manifest**: 运行结束生成 `artifacts/manifest.json`（所有产物路径 + sha256）
- **自动补齐**: 检测到缺少 ERA5 评估真值时自动触发下载

### 跳过已通过阶段
```bash
bash scripts/one_shot_verify.sh --yes \
  --skip-cpu-smoke \
  --skip-gpu-smoke \
  --skip-rmse
```

### 查看产物清单
```bash
cat artifacts/manifest.json | python3 -m json.tool
```

## 常见故障排查

### 1. SSH 断线导致任务中断
**推荐方案**: 始终在 tmux/screen 中运行长任务：
```bash
tmux new -s work 'bash scripts/one_shot_verify.sh --yes'
# 断线后: tmux attach -t work
```

**nohup 方案**:
```bash
nohup bash scripts/one_shot_verify.sh --yes > verify.log 2>&1 &
# 查看进度: tail -f verify.log
```

### 2. 缺少 ERA5 评估真值文件
**症状**: Day5 RMSE 报 `FileNotFoundError: era5_pressure_2023071000.nc`
**原因**: `prepare_era5_inputs.sh` 在 processed npy 存在时跳过了 raw nc 下载
**修复**:
```bash
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt
```

### 3. nohup 日志空白/无 traceback
**原因**: Python 默认缓冲 stdout
**修复**: 使用 `one_shot_verify.sh`（已设置 PYTHONUNBUFFERED=1 和 PYTHONFAULTHANDLER=1）

### 4. 在错误 Python 环境运行
**症状**: `ModuleNotFoundError: No module named 'netCDF4'`（系统 python）
**修复**:
```bash
source scripts/env_gpu.sh   # 激活正确环境
# 或直接用 run_gpu.sh 运行
scripts/run_gpu.sh tools/eval_rmse.py --pred ...
```

### 5. 容器无 rg (ripgrep)
脚本已避免依赖 rg，所有搜索使用 bash 内建 + grep。

### 6. 绘图依赖缺失
**症状**: `run_product_all.sh` 报 `missing plotting deps (matplotlib/scipy)`
**修复**:
```bash
bash scripts/install_extras.sh plots --force
```

### 7. 容器无 dmesg 权限
`one_shot_verify.sh` 使用应用层诊断（df/ps），不依赖 dmesg。

### 8. 重复启动核查脚本
**症状**: `检测到已有运行实例 (PID=xxxx)`
**修复**:
```bash
# 强制接管
bash scripts/one_shot_verify.sh --yes --force-kill

# 或手动清除锁
rm .one_shot_verify.lock
```

### 9. `CUDAExecutionProvider missing`
```bash
bash scripts/create_gpu_venv.sh --update
source scripts/env_gpu.sh
```

### 10. 360h OOM
```bash
bash scripts/run_360h_split.sh --auto-retry
```

### 11. `blueprint unavailable (No module named 'cmaps')`
```bash
source scripts/env_gpu.sh
uv pip install --python .venv-gpu/bin/python cmaps pandas xarray
```

### 12. Streamlit 外网 503
使用 SSH 隧道，浏览器访问 `http://127.0.0.1:8501`。

### 13. `git pull/fetch` TLS 中断（AutoDL 常见）
```bash
git config --global http.version HTTP/1.1
git config --global http.lowSpeedLimit 1
git config --global http.lowSpeedTime 60
for i in 1 2 3 4 5; do
  timeout 60 git fetch origin main && break
  sleep 3
done
git pull --rebase origin main
```

## 关机前清理（可选）
```bash
bash scripts/internal/cleanup_check.sh
bash scripts/internal/cleanup_autodl.sh --dry-run
bash scripts/internal/cleanup_autodl.sh --force --keep-latest 2 --keep-days 3
```

## 说明
- 对外只需 `scripts/` 顶层入口。
- `scripts/internal/` 与 `docs/_internal/` 是内部流程，不影响复现主链。
- 所有脚本兼容 bash，不依赖 rg/dmesg 等外部工具。
