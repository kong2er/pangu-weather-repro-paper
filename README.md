# Pangu-Weather Repro (Delivery Edition)

本仓库面向“阶段化可复现交付”。复现人员只看三份文档即可：
- `README.md`：最短执行路径
- `RUNBOOK.md`：S1-S8 详细步骤与排错
- `docs/DELIVERY_SUMMARY.md`：阶段目标、产物、验收矩阵

## 最短复现路径（新机器推荐）
```bash
cd /root/projects/pangu-weather-repro-uv
bash scripts/create_cpu_venv.sh
bash scripts/create_gpu_venv.sh
source scripts/env_gpu.sh && source configs/default.env
bash scripts/run_360h_split.sh --auto-retry
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --impl auto --force
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```

## 官方入口（只用 `scripts/`）
- 环境：`create_cpu_venv.sh`、`create_gpu_venv.sh`、`env_cpu.sh`、`env_gpu.sh`
- 运行：`run_cpu.sh`、`run_gpu.sh`、`run_360h_split.sh`、`run_product_all.sh`、`run_streamlit.sh`
- 验收：`verify_repo_health.sh`、`final_verify.sh`
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

## 产品图实现选择
`run_product_all.sh` 支持 `--impl`：
- `auto`：默认，优先稳定
- `native`：本仓库原生实现
- `blueprint`：蓝本适配实现

示例：
```bash
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --impl blueprint --force
```

## 常见故障快速修复
- `CUDAExecutionProvider` 缺失：
```bash
bash scripts/create_gpu_venv.sh --update
source scripts/env_gpu.sh
```
- 绘图依赖缺失（matplotlib/cartopy/scipy）：
```bash
bash scripts/install_extras.sh plots --force
```
- 输出目录已存在：使用 `--force` 或切换 `--out-dir`
- 360h OOM：`bash scripts/run_360h_split.sh --auto-retry`
- Streamlit 外网 503：优先 SSH 隧道访问 `http://127.0.0.1:8501`

## 目录说明（复现视角）
- `pangu_weather_repro/`：核心代码
- `scripts/`：公开入口
- `tools/`：高级 CLI
- `configs/`：路径与环境配置
- `docs/`：对外交付文档
- `vendor/blueprint/`：蓝本镜像与适配基础

运行产物默认写入 `OUTPUT_ROOT`（一般为 `/root/autodl-tmp/pangu-weather-repro/outputs`）。
