# Pangu-Weather 复现指南

**从零复现 Pangu-Weather 360h 预测并生成论文级图表。**

> **论文引用**
> Bi, K., Xie, L., Zhang, H., Chen, X., Gu, X., & Tian, Q. (2023).
> *Accurate medium-range global weather forecasting with 3D neural networks.*
> Nature, 619, 533-538. https://doi.org/10.1038/s41586-023-06185-3

本仓库将 Pangu-Weather 官方 ONNX 权重 + ERA5 初始场，通过阶段化流程（S1-S8）完成：环境搭建 → 推理 → RMSE 评估 → 论文图 / 产品图 → 最终验收。整套流程在 RTX 4090 上约 **1-2 小时**即可完成（含数据下载）。

---

## 目录

1. [环境要求](#1-环境要求)
2. [AutoDL 开机设置（新人从零）](#2-autodl-开机设置新人从零)
3. [一键复现（最快路径）](#3-一键复现最快路径)
4. [分阶段详细指南（S1-S8）](#4-分阶段详细指南s1-s8)
5. [预期结果总览](#5-预期结果总览)
6. [SSH 断线应对速查](#6-ssh-断线应对速查)
7. [常见故障排查](#7-常见故障排查)
8. [目录结构说明](#8-目录结构说明)
9. [扩展文档索引](#9-扩展文档索引)

---

## 1. 环境要求

| 项目 | 要求 |
|------|------|
| GPU | NVIDIA RTX 4090（24 GB）或同等 |
| CUDA | 11.8+ |
| 系统 | Linux（Ubuntu 20.04 / 22.04） |
| Python | 3.10 ~ 3.11 |
| 磁盘 | >= 50 GB（数据盘，AutoDL 为 `/root/autodl-tmp`） |
| 网络 | 需访问 HuggingFace / CDS API（首次下载） |

---

## 2. AutoDL 开机设置（新人从零）

### 2.1 选择镜像

在 AutoDL 创建实例时，选择：

- **基础镜像**：PyTorch 2.x / CUDA 11.8 / Python 3.10
- **GPU**：RTX 4090（24 GB）

### 2.2 SSH 连接

实例启动后，AutoDL 会提供 SSH 登录命令，格式如：

```bash
ssh -p <端口> root@connect.westb.seetacloud.com
```

在本地终端粘贴执行即可连接。

### 2.3 首次 clone 仓库

```bash
mkdir -p /root/projects && cd /root/projects
git clone git@github.com:kong2er/pangu-weather-repro-paper.git
cd pangu-weather-repro-paper
```

### 2.4 安装 tmux（防断线，必装）

AutoDL 容器默认不带 tmux，**必须先装**，否则执行 tmux 命令会导致 SSH 断开：

```bash
apt update && apt install -y tmux
```

常用操作：

| 操作 | 命令 |
|------|------|
| 新建会话 | `tmux new -s work` |
| 断开（不关闭） | `Ctrl+B` 然后按 `D` |
| 重连 | `tmux attach -t work` |
| 列出所有会话 | `tmux ls` |

在 tmux 内运行长时间任务，即使 SSH 断开也不会丢失进度。

### 2.5 配置 CDS API Key

ERA5 数据自动下载需要 CDS API 密钥。前往 https://cds.climate.copernicus.eu 注册并获取 API Key，然后创建配置文件：

```bash
cat > ~/.cdsapirc << 'EOF'
url: https://cds.climate.copernicus.eu/api/v2
key: <你的UID>:<你的API-Key>
EOF
chmod 600 ~/.cdsapirc
```

> **无外网时**：可跳过此步，手动将 ERA5 nc 文件放置到 `$ERA5_RAW_ROOT` 目录（见 [S3 数据准备](#s3-数据准备--gpu-冒烟)）。

---

## 3. 一键复现（最快路径）

以下命令从零到完成，推荐在 tmux 会话中执行：

```bash
cd /root/projects/pangu-weather-repro-paper
apt update && apt install -y tmux                          # 首次需安装 tmux
bash scripts/create_cpu_venv.sh && bash scripts/create_gpu_venv.sh
source scripts/env_gpu.sh && source configs/default.env
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt
tmux new -s repro 'bash scripts/run_360h_split.sh --auto-retry && bash scripts/one_shot_verify.sh --yes'
# 断线后重连: tmux attach -t repro
```

`one_shot_verify.sh` 会自动完成：环境预检 → CPU/GPU 冒烟 → ERA5 真值检查 → **rollout 数据生成** → RMSE 评估 → 论文图 → 产品图 → E 阶段验收 → manifest 生成。

**预计总耗时**：约 1-2 小时（含数据下载，RTX 4090 基准）。

---

## 4. 分阶段详细指南（S1-S8）

### S1 环境搭建

| | |
|---|---|
| **耗时估算** | 5-10 min |
| **通过标准** | `env_gpu.sh` 输出包含 `CUDAExecutionProvider` |

```bash
cd /root/projects/pangu-weather-repro-paper

# 创建 CPU / GPU 虚拟环境
bash scripts/create_cpu_venv.sh
bash scripts/create_gpu_venv.sh

# 激活 GPU 环境 + 加载路径配置
source scripts/env_gpu.sh
source configs/default.env

# 安装可选依赖（RMSE、绘图、Streamlit）
bash scripts/install_extras.sh rmse          # netCDF4, cftime
bash scripts/install_extras.sh plots --force # matplotlib, cartopy, scipy
bash scripts/install_extras.sh streamlit     # Streamlit 页面

# 验证环境健康
bash scripts/verify_repo_health.sh
```

预期输出：终端显示 `CUDAExecutionProvider` 已加载，健康检查通过。

---

### S2 CPU 冒烟

| | |
|---|---|
| **耗时估算** | < 1 min |
| **通过标准** | 输出 `contracts smoke ok` |

```bash
bash scripts/run_cpu.sh -m pangu_weather_repro.smoke
```

预期输出：
```
contracts smoke ok
```

---

### S3 数据准备 + GPU 冒烟

| | |
|---|---|
| **耗时估算** | 10-30 min（取决于网速） |
| **通过标准** | 生成 `$OUTPUT_ROOT/smoke_24h_report.json` |

```bash
# 下载 ERA5 推理输入 + 评估真值（非交互模式）
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt

# 运行 GPU 24h 冒烟测试
bash scripts/run_day3_smoke_gpu.sh
```

数据准备脚本会自动完成：
1. 下载 ERA5 单层 / 气压层 nc 文件到 `$ERA5_RAW_ROOT`
2. 预处理为 `$PROCESSED_ROOT/surface.npy` + `pressure.npy`
3. 下载 RMSE 评估所需的真值 nc 文件

> **无外网时手动放置**：
> - 推理输入：`$ERA5_RAW_ROOT/era5_single_2023070900.nc` + `era5_pressure_2023070900.nc`
> - 或预处理后：`$PROCESSED_ROOT/surface.npy` + `pressure.npy`
> - 评估真值：`$ERA5_RAW_ROOT/era5_pressure_2023071000.nc`（init+24h）、`era5_pressure_2023071006.nc`（init+30h）

---

### S4 84h 短时效推理

| | |
|---|---|
| **耗时估算** | 5-10 min |
| **通过标准** | 输出目录含 `forecast_report.json` |

```bash
scripts/run_gpu.sh tools/run_forecast.py \
  --strategy kong2er_ref \
  --mode short \
  --target-hours 84 \
  --noarena --threads 1 \
  --out-dir "$OUTPUT_ROOT/forecast_84h_$(date +%Y%m%d_%H%M%S)"
```

---

### S5 360h 长时效推理

| | |
|---|---|
| **耗时估算** | 15-30 min |
| **通过标准** | 终端出现 `report long` 或 `[RETRY] success` |

```bash
# 推荐在 tmux 中运行（防断线）
tmux new -s forecast 'bash scripts/run_360h_split.sh --auto-retry'

# 或直接运行
bash scripts/run_360h_split.sh --auto-retry
```

脚本自动分段推理并在 OOM 时自动降载重试。

---

### S6 RMSE 评估 + 论文图

| | |
|---|---|
| **耗时估算** | 5-10 min |
| **通过标准** | `artifacts/day5/rmse.csv` 和 `figures/day6/*.png` 存在且非空 |

```bash
# 确保评估真值已下载
bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt

# RMSE 评估
bash scripts/internal/run_day5_rmse.sh --force

# 生成论文级图表
bash scripts/internal/run_day6_plots.sh --force
```

---

### S7 产品图族 + Streamlit

| | |
|---|---|
| **耗时估算** | 5-10 min |
| **通过标准** | `figures/product/*.png` 和 `*.json` 生成；Streamlit 页面可访问 |

```bash
# 生成产品图（填色图、差值图、矢量图、风速图、海平面气压+风场）
bash scripts/run_product_all.sh \
  --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" \
  --hours 24,30 \
  --impl auto \
  --force

# 启动 Streamlit 可视化页面
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
```

> **Streamlit 访问**：本地浏览器打开 `http://127.0.0.1:8501`。如外网 503，请使用 SSH 隧道转发端口。

---

### S8 最终验收

| | |
|---|---|
| **耗时估算** | 2-5 min |
| **通过标准** | 输出 `FINAL VERIFY PASS` |

```bash
# 方式 1：一键核查（推荐）
bash scripts/one_shot_verify.sh --yes

# 方式 2：传统分步验收
bash scripts/verify_repo_health.sh
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```

验收通过后会生成 `artifacts/manifest.json`（所有产物路径 + SHA256 校验和）。

---

### 耗时汇总

| 阶段 | 耗时 |
|------|------|
| S1 环境搭建 | 5-10 min |
| S2 CPU 冒烟 | < 1 min |
| S3 数据下载 + 预处理 + GPU 冒烟 | 10-30 min（取决于网速） |
| S4 84h 推理 | 5-10 min |
| S5 360h 推理 | 15-30 min |
| S6 RMSE + 出图 | 5-10 min |
| S7 产品图 | 5-10 min |
| S8 验收 | 2-5 min |
| **总计** | **约 1-2 小时**（含数据下载） |

---

## 5. 预期结果总览

| 产物文件 | 说明 |
|----------|------|
| `$OUTPUT_ROOT/smoke_24h_report.json` | GPU 24h 冒烟测试报告 |
| `$OUTPUT_ROOT/forecast_84h_*/forecast_report.json` | 84h 短时效推理报告 |
| `$OUTPUT_ROOT/day4_rollout_30h/` | 360h 逐步推理输出（surface/pressure npy） |
| `artifacts/day5/rmse.csv` | RMSE 评估结果（各变量、各时效） |
| `figures/day6/*.png` | 论文级图表（场图 + RMSE 曲线） |
| `figures/product/*.png` | 产品图族（填色、差值、矢量、风速、海平面气压+风场） |
| `figures/product/*.json` | 产品图元数据 |
| `artifacts/day7/REPORT.md` | 验收报告 |
| `artifacts/day7/E_STAGE_REPORT.md` | E 阶段验收报告 |
| `artifacts/manifest.json` | 全部产物路径 + SHA256 校验和 |
| `logs/one_shot_verify_*.log` | 一键核查完整日志 |

> **数据路径说明**：`$OUTPUT_ROOT` 默认为 `/root/autodl-tmp/pangu-weather-repro/outputs`，由 `configs/default.env` 定义。

---

## 6. SSH 断线应对速查

| 场景 | 操作 |
|------|------|
| tmux 断线后重连 | `tmux attach -t verify`（或 `-t forecast`） |
| nohup 查看日志 | `tail -f verify.log` 或 `tail -f logs/one_shot_verify_*.log` |
| screen 断线后重连 | `screen -r verify` |
| 查看最新日志文件 | `ls -lt logs/one_shot_verify_*.log \| head -1` |
| 检查任务是否在运行 | `cat .one_shot_verify.lock && ps -p $(cat .one_shot_verify.lock)` |
| 强制重跑核查 | `bash scripts/one_shot_verify.sh --force-kill --yes` |
| nohup 方式运行 | `nohup bash scripts/one_shot_verify.sh --yes > verify.log 2>&1 &` |

---

## 7. 常见故障排查

| 故障现象 | 原因 | 修复命令 |
|----------|------|----------|
| `tmux: command not found` 后 SSH 断开 | AutoDL 容器未预装 tmux | `apt update && apt install -y tmux` |
| `SSL_CERTIFICATE_VERIFY_FAILED` | AutoDL 容器缺少 CA 证书 | 脚本已自动降级为 `verify=False`；或 `source configs/default.env` |
| RMSE 缺少 `eval_z500.npz` | Day4 rollout 未运行 | `one_shot_verify.sh` 已自动补跑；或手动：`scripts/run_gpu.sh tools/day4_rollout.py --steps 24,6 --noarena --out-dir "$OUTPUT_ROOT/day4_rollout_30h"` |
| `CUDAExecutionProvider` 缺失 | GPU 环境未正确安装或未激活 | `bash scripts/create_gpu_venv.sh --update && source scripts/env_gpu.sh` |
| `libcublasLt.so.12 MISSING` | CUDA 库不在 `LD_LIBRARY_PATH` | `source scripts/env_gpu.sh` |
| 绘图依赖缺失（matplotlib/scipy） | 可选依赖未安装 | `bash scripts/install_extras.sh plots --force` |
| RMSE 依赖缺失（netCDF4） | 可选依赖未安装 | `bash scripts/install_extras.sh rmse` |
| 缺少 ERA5 推理输入 | 数据未下载 | `bash scripts/prepare_era5_inputs.sh --yes` |
| 缺少 ERA5 评估真值 | 评估真值未单独下载 | `bash scripts/prepare_era5_inputs.sh --yes --ensure-eval-gt` |
| 360h 推理 OOM | GPU 显存不足 | `bash scripts/run_360h_split.sh --auto-retry`（自动降载） |
| Streamlit 外网 503 | 外部网络访问被拦截 | 使用 SSH 隧道 `ssh -L 8501:127.0.0.1:8501 ...` |
| 已有核查在运行 | lockfile 冲突 | `bash scripts/one_shot_verify.sh --force-kill --yes` |
| Python 环境不对 / ModuleNotFoundError | 未 source 环境脚本 | 确保先执行 `source scripts/env_gpu.sh` |
| nohup 日志空白 | Python 输出缓冲 | 使用 `one_shot_verify.sh`（已内置 `PYTHONUNBUFFERED=1`） |
| tmux `[exited]` 不知结果 | 脚本已结束（成功或失败） | `cat logs/one_shot_verify_*.log \| tail -50` 查看日志 |

---

## 8. 目录结构说明

```
pangu-weather-repro-paper/
├── pangu_weather_repro/        # 核心 Python 包（推理、可视化、Streamlit app）
│   ├── contracts.py            #   张量契约检查
│   ├── smoke.py                #   CPU 冒烟测试
│   ├── infer/                  #   ONNX 推理引擎（runner.py, scheduler.py）
│   ├── visualization/          #   绘图模块（product_draw, geo, style）
│   └── app/                    #   Streamlit 应用（app.py + pages/）
│
├── scripts/                    # 公开入口脚本（S1-S8 所有命令都在这里）
│   ├── create_cpu_venv.sh      #   创建 CPU 虚拟环境
│   ├── create_gpu_venv.sh      #   创建 GPU 虚拟环境
│   ├── env_cpu.sh / env_gpu.sh #   激活环境 + 设置 CUDA/SSL 路径
│   ├── install_extras.sh       #   安装可选依赖（rmse/plots/streamlit）
│   ├── prepare_era5_inputs.sh  #   ERA5 数据下载与预处理
│   ├── run_cpu.sh              #   CPU 冒烟
│   ├── run_day3_smoke_gpu.sh   #   GPU 冒烟
│   ├── run_gpu.sh              #   GPU 推理封装
│   ├── run_360h_split.sh       #   360h 分段推理（含 auto-retry）
│   ├── run_product_all.sh      #   产品图族生成
│   ├── run_streamlit.sh        #   启动 Streamlit
│   ├── one_shot_verify.sh      #   一键核查（S1-S8 全流程）
│   ├── verify_repo_health.sh   #   轻量健康检查
│   ├── final_verify.sh         #   传统验收
│   └── internal/               #   内部脚本（RMSE、出图、清理等）
│
├── tools/                      # 高级 CLI 工具
│   ├── run_forecast.py         #   统一推理 CLI
│   ├── eval_rmse.py            #   RMSE 评估
│   ├── plot_fields.py          #   场图绘制
│   ├── plot_rmse_curve.py      #   RMSE 曲线
│   ├── plot_paper_bundle.py    #   论文图表包
│   └── plot_product_bundle.py  #   产品图包
│
├── configs/
│   ├── default.env             # 路径配置（DATA_ROOT, OUTPUT_ROOT 等）
│   └── default.yaml            # YAML 配置
│
├── tests/                      # 单元测试
├── vendor/blueprint/           # 蓝本参考实现镜像
├── artifacts/                  # 产物（rmse.csv, manifest.json, 报告）
├── figures/                    # 图表输出（day6/ 论文图, product/ 产品图）
├── outputs/                    # 推理输出（gitignored）
├── docs/                       # 扩展文档
└── logs/                       # 核查日志
```

**数据盘路径**（由 `configs/default.env` 配置）：

| 变量 | 默认路径 | 用途 |
|------|----------|------|
| `$DATA_ROOT` | `/root/autodl-tmp/pangu-weather-repro` | 数据根目录 |
| `$ERA5_RAW_ROOT` | `$DATA_ROOT/era5_raw` | ERA5 原始 nc 文件 |
| `$PROCESSED_ROOT` | `$DATA_ROOT/processed` | 预处理后 npy 文件 |
| `$OUTPUT_ROOT` | `$DATA_ROOT/outputs` | 推理输出 |
| `$MODELS_ROOT` | `$DATA_ROOT/models` | ONNX 模型权重 |
| `$CACHE_ROOT` | `$DATA_ROOT/cache` | 缓存 |
| `$LOG_ROOT` | `$DATA_ROOT/logs` | 日志 |

---

## 9. 扩展文档索引

| 文档 | 内容 |
|------|------|
| [`RUNBOOK.md`](RUNBOOK.md) | S1-S8 分阶段详细操作手册（含排错） |
| [`docs/DELIVERY_SUMMARY.md`](docs/DELIVERY_SUMMARY.md) | 阶段目标、命令、产物、验收矩阵速查表 |
| [`docs/FUNCTION_CALL_MANUAL_ZH.md`](docs/FUNCTION_CALL_MANUAL_ZH.md) | 16 个核心功能调用速查（中文） |
| [`docs/_internal/`](docs/_internal/) | 内部流程文档（不影响主线复现） |
