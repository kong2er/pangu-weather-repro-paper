# Pangu-Weather Repro (Delivery Edition)

本仓库用于“可复现交付”：按 S1-S8 阶段执行即可完成环境、推理、评估、可视化与最终验收。

## 对外文档三件套
- `README.md`：最短命令入口（本文件）
- `RUNBOOK.md`：详细阶段说明与排错
- `docs/DELIVERY_SUMMARY.md`：S1-S8 一页总览

## S1-S8 最短主线（可复制）
```bash
cd /root/projects/pangu-weather-repro-uv
bash scripts/create_cpu_venv.sh
bash scripts/create_gpu_venv.sh
source scripts/env_gpu.sh && source configs/default.env
bash scripts/run_360h_split.sh --auto-retry
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```

## 阶段入口（官方）
- S1 环境：`scripts/create_cpu_venv.sh`、`scripts/create_gpu_venv.sh`、`source scripts/env_cpu.sh`、`source scripts/env_gpu.sh`
- S2 CPU smoke：`scripts/run_cpu.sh -m pangu_weather_repro.smoke`
- S3 GPU smoke：`bash scripts/final_verify.sh`（内含 day3/day5/day6 主链）
- S4 84h 推理：`scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --target-hours 84 --noarena --threads 1`
- S5 360h 推理：`bash scripts/run_360h_split.sh --auto-retry`
- S6 RMSE + paper：`bash scripts/final_verify.sh`（内含）
- S7 产品图 + Streamlit：`bash scripts/run_product_all.sh ...`、`bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501`
- S8 最终验收：`bash scripts/verify_repo_health.sh`、`bash scripts/final_verify.sh --with-e-stage --e-stage-force`

## Blueprint 对齐实现选择
产品图支持实现选择：
- `--impl auto`（默认，优先稳定）
- `--impl native`
- `--impl blueprint`

示例：
```bash
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --impl blueprint --force
```

## Streamlit 访问
```bash
bash scripts/install_extras.sh streamlit
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
```
若外网 503，优先使用 SSH 隧道访问本地 `http://127.0.0.1:8501`（详见 `RUNBOOK.md`）。

## 常见问题（最短）
- GPU provider 缺失：`bash scripts/create_gpu_venv.sh --update && source scripts/env_gpu.sh`
- netCDF4 缺失：`bash scripts/install_extras.sh rmse`
- matplotlib/cartopy/scipy 缺失：`bash scripts/install_extras.sh plots --force`
- 输出目录已存在：加 `--force` 或换 `--out-dir`
- OOM：`bash scripts/run_360h_split.sh --auto-retry`

## 目录说明（复现者视角）
- `pangu_weather_repro/`：核心包代码
- `scripts/`：官方入口脚本（只看这里）
- `tools/`：高级 CLI（脚本内部调用）
- `configs/`：环境与路径配置
- `docs/`：交付文档（对外）
- `vendor/blueprint/`：蓝本镜像代码（对齐参考）
- 运行产物默认落在 `OUTPUT_ROOT`（通常 `/root/autodl-tmp/pangu-weather-repro/outputs`）

## 产物与 Git 规则
- `figures/`、`outputs/`、`artifacts/` 默认只追踪 `.gitkeep`/README/小报告
- 不提交 `.venv-*`、模型文件、npy/npz/png/tgz 等大产物
