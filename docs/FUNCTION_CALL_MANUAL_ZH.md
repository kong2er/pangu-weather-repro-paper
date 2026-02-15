# 功能调用说明书（中文）

本文档面向复现执行人员，按"功能 -> 命令 -> 实际意义"给出可直接复制的调用方式。

## 0. 一键核查（推荐入口）
- 命令（SSH 断线安全）：
```bash
# 方式 1: tmux（推荐）
tmux new -s verify 'bash scripts/one_shot_verify.sh --yes'
# 断线后重连: tmux attach -t verify

# 方式 2: nohup
nohup bash scripts/one_shot_verify.sh --yes > verify.log 2>&1 &
tail -f verify.log
```
- 实际意义：自动完成全链路核查（环境检测 -> CPU/GPU 冒烟 -> 评估真值 -> RMSE -> 出图 -> 产品图 -> E 阶段 -> manifest），统一日志、并发保护、产物校验。
- 选项说明：
  - `--yes`：非交互模式，跳过所有确认
  - `--force`：强制重新生成所有产物
  - `--force-kill`：强制终止已有运行实例
  - `--skip-cpu-smoke`：跳过 CPU 冒烟
  - `--skip-gpu-smoke`：跳过 GPU 冒烟
  - `--skip-rmse`：跳过 RMSE
  - `--skip-plots`：跳过出图
  - `--skip-product`：跳过产品图
  - `--no-eval-gt`：不下载评估真值

## 1. 环境初始化（CPU/GPU）

> **前置要求**：本项目使用 [uv](https://github.com/astral-sh/uv)（Rust 实现的 Python 包管理器）作为唯一包管理工具。请确保 uv >= 0.4 已安装：
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc
> uv --version  # 验证
> ```

- 命令：
```bash
bash scripts/create_cpu_venv.sh
bash scripts/create_gpu_venv.sh
```
- 实际意义：通过 uv 创建并维护幂等虚拟环境，避免不同机器依赖漂移。

## 2. 环境切换
- CPU：
```bash
source scripts/env_cpu.sh
```
- GPU：
```bash
source scripts/env_gpu.sh
```
- 实际意义：确保后续命令使用正确解释器与运行上下文。
- 常见错误：不 source 环境直接用系统 python 运行，会导致 `ModuleNotFoundError`。

## 3. CPU 冒烟测试（Day8）
- 命令：
```bash
bash scripts/internal/run_day8_cpu_smoke.sh
```
- 实际意义：快速验证包结构、输入输出契约、基础执行链路。

## 4. Day3 前置数据准备（ERA5 -> numpy）
- 推理输入（必需）：
```bash
# 交互模式
bash scripts/prepare_era5_inputs.sh

# 非交互模式（SSH 不稳定时推荐）
bash scripts/prepare_era5_inputs.sh --yes
```
- 推理输入 + 评估真值（推荐）：
```bash
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt
```
- 实际意义：
  - 推理输入：生成 Day3 所需的 `processed/surface.npy` 和 `processed/pressure.npy`
  - 评估真值：下载 Day5 RMSE 评估需要的 ERA5 pressure nc 文件（如 `era5_pressure_2023071000.nc`）
- 低网速 / 无外网场景：
  - 可手动放置原始 `era5_single_*.nc + era5_pressure_*.nc` 或直接放置 `surface.npy + pressure.npy`
  - 评估真值也需手动放置对应时刻的 `era5_pressure_*.nc` 文件
- 自定义数据集：
```bash
bash scripts/prepare_era5_inputs.sh --dataset-mode custom
```
- 选项：
  - `--date YYYYMMDD`：初始场日期
  - `--hour HH`：初始场小时
  - `--yes`：非交互模式
  - `--force-preprocess`：强制重新预处理
  - `--ensure-eval-gt`：同时下载评估真值
  - `--eval-steps STEPS`：评估步长（默认 "24,6"）

## 5. GPU 冒烟测试（Day3）
- 命令：
```bash
bash scripts/internal/run_day3_smoke_gpu.sh
```
- 实际意义：验证 24h 模型可在 GPU 侧正常推理并生成 smoke 报告。

## 6. 84h 推理（短时效）
- 命令：
```bash
scripts/run_gpu.sh tools/run_forecast.py \
  --strategy kong2er_ref \
  --mode short \
  --target-hours 84 \
  --noarena --threads 1 \
  --out-dir "$OUTPUT_ROOT/forecast_84h_$(date +%Y%m%d_%H%M%S)"
```
- 实际意义：验证短时效预测链路与调度策略。

## 7. 360h 稳态推理（推荐）
- 命令：
```bash
# 推荐在 tmux 中运行（防止 SSH 断线）
tmux new -s forecast 'bash scripts/run_360h_split.sh --auto-retry'
# 断线后: tmux attach -t forecast
```
- 实际意义：分段推理 + 自动降载重试，降低 OOM 风险，适合云端稳定执行。

## 8. RMSE 评估（Day5）
- 命令：
```bash
# 先确保评估真值存在（重要！）
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt

# 再运行 RMSE
bash scripts/internal/run_day5_rmse.sh --force
```
- 实际意义：生成误差评估结果（`artifacts/day5/rmse.csv`），用于量化预测质量。
- 常见错误：缺少 ERA5 评估真值文件。修复方法见上方"先确保评估真值存在"。

## 9. 论文图生成（Day6）
- 命令：
```bash
bash scripts/internal/run_day6_plots.sh --force
```
- 实际意义：生成字段图和 RMSE 曲线图，形成论文图产物。

## 10. 产品图族（E 阶段）
- 一键命令：
```bash
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --impl auto --force
```
- 实际意义：批量生成 fill/diff/vector/wind_speed/msl_wind 图和对应元数据 JSON。
- 如果提示缺绘图依赖：
```bash
bash scripts/install_extras.sh plots --force
```

## 11. Streamlit 页面
- 命令：
```bash
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
```
- 实际意义：可视化查看 Home / Forecast / Plots 页面内容。
- 外网 503 时：通过 SSH 隧道访问 `http://127.0.0.1:8501`。

## 12. 轻量健康检查
- 命令：
```bash
bash scripts/verify_repo_health.sh
```
- 实际意义：快速验证入口脚本、核心导入和测试状态，不跑重推理。

## 13. 最终全链验收
- 推荐（一键核查）：
```bash
bash scripts/one_shot_verify.sh --yes
```
- 传统方式：
```bash
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```
- 实际意义：串联 CPU/GPU/评估/绘图/E 阶段核查，输出最终 PASS 结论。

## 14. 关机前空间清理（可选）
- 先看占用：
```bash
bash scripts/internal/cleanup_check.sh
```
- 预览清理：
```bash
bash scripts/internal/cleanup_autodl.sh --dry-run
```
- 执行清理：
```bash
bash scripts/internal/cleanup_autodl.sh --force --keep-latest 2 --keep-days 3
```
- 实际意义：删除可再生成的临时产物与缓存，保留模型与关键数据目录。

## 15. 查看产物清单
- 命令：
```bash
cat artifacts/manifest.json | python3 -m json.tool
```
- 实际意义：查看所有关键产物的路径、大小、sha256 校验值，用于交付确认。

## 16. 推荐执行顺序

### 最短路径（一键）
```bash
# 0. 确保 uv 已安装
uv --version || { curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc; }

bash scripts/create_cpu_venv.sh && bash scripts/create_gpu_venv.sh
source scripts/env_gpu.sh && source configs/default.env
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt
bash scripts/run_360h_split.sh --auto-retry
bash scripts/one_shot_verify.sh --yes
```

### 分步路径
1. S1：创建并激活环境
2. S2-S3：CPU/GPU 冒烟
3. S4-S5：84h 与 360h 推理
4. S6-S7：评估与图像（先运行 `--ensure-eval-gt` 确保真值就绪）
5. S8：最终验收

## 17. SSH 断线应对速查

| 操作 | 命令 |
|------|------|
| tmux 中运行 | `tmux new -s verify 'bash scripts/one_shot_verify.sh --yes'` |
| 重连 tmux | `tmux attach -t verify` |
| nohup 后台运行 | `nohup bash scripts/one_shot_verify.sh --yes > verify.log 2>&1 &` |
| 查看 nohup 进度 | `tail -f verify.log` |
| 查看最新日志 | `ls -lt logs/one_shot_verify_*.log \| head -1` |
| 检查是否在运行 | `cat .one_shot_verify.lock && ps -p $(cat .one_shot_verify.lock)` |
| 强制重跑 | `bash scripts/one_shot_verify.sh --yes --force-kill` |
