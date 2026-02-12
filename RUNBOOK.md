# RUNBOOK (Stage-by-Stage Reproduction)

本手册只服务复现执行。内部治理材料已归档到 `docs/_internal/`。

## 0. 预设
```bash
cd /root/projects/pangu-weather-repro-uv
source configs/default.env
```

## S1 环境与依赖
CPU：
```bash
bash scripts/create_cpu_venv.sh
source scripts/env_cpu.sh
```
GPU：
```bash
bash scripts/create_gpu_venv.sh
source scripts/env_gpu.sh
```
可选扩展依赖：
```bash
bash scripts/install_extras.sh rmse
bash scripts/install_extras.sh plots --force
bash scripts/install_extras.sh streamlit
```

验收：
```bash
bash scripts/verify_repo_health.sh
```

## S2 CPU smoke
```bash
scripts/run_cpu.sh -m pangu_weather_repro.smoke
```
预期：输出 `contracts smoke ok`。

## S3 GPU smoke（主链起点）
```bash
bash scripts/final_verify.sh
```
预期：至少通过 Day3 smoke、Day5 RMSE、Day6 plots。

## S4 84h 推理
```bash
scripts/run_gpu.sh tools/run_forecast.py \
  --strategy kong2er_ref \
  --mode short \
  --target-hours 84 \
  --noarena --threads 1 \
  --out-dir "$OUTPUT_ROOT/forecast_84h_$(date +%Y%m%d_%H%M%S)"
```

## S5 360h 推理（稳态推荐）
```bash
bash scripts/run_360h_split.sh --auto-retry
```
说明：自动分段 + 失败降载重试（避免 OOM 全盘中断）。

## S6 RMSE + Paper 图
主线已在 `final_verify.sh` 内执行。单独跑可用内部脚本：
```bash
bash scripts/internal/run_day5_rmse.sh --force
bash scripts/internal/run_day6_plots.sh --force
```

## S7 产品图族 + Streamlit
一键产品图：
```bash
bash scripts/run_product_all.sh \
  --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" \
  --hours 24,30 --impl auto --force
```

蓝本对齐实现：
```bash
bash scripts/run_product_all.sh \
  --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" \
  --hours 24,30 --impl blueprint --force
```

启动页面：
```bash
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
```

## S8 最终验收
```bash
bash scripts/verify_repo_health.sh
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```
预期：`FINAL VERIFY PASS`。

## 排错（最常见）
1. `CUDAExecutionProvider missing`
```bash
bash scripts/create_gpu_venv.sh --update
source scripts/env_gpu.sh
```

2. `out_dir exists`
- 加 `--force`，或切换新 `--out-dir`。

3. 360h OOM
```bash
bash scripts/run_360h_split.sh --auto-retry
```

4. `blueprint unavailable (No module named 'cmaps')`
```bash
source scripts/env_gpu.sh
scripts/run_gpu.sh -m pip install -U cmaps pandas xarray
```

5. Streamlit 外网 503
- 优先 SSH 隧道：本地访问 `http://127.0.0.1:8501`。

## 清理空间（关机前）
只看占用：
```bash
bash scripts/internal/cleanup_check.sh
```
真清理（默认保守保留，建议先 dry-run）：
```bash
bash scripts/internal/cleanup_autodl.sh --dry-run
bash scripts/internal/cleanup_autodl.sh --force --keep-latest 2 --keep-days 3
```

## 备注
- 官方入口在 `scripts/`。
- 研发/归档入口在 `scripts/internal/` 与 `docs/_internal/`，不建议复现人员直接使用。
