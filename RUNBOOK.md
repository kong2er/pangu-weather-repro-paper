# RUNBOOK (Stage-by-Stage Reproduction)

本手册给复现人员使用。按 S1-S8 顺序执行即可。

## S0 预设
```bash
cd /root/projects/pangu-weather-repro-paper
source configs/default.env
```

## S1 环境与依赖
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
bash scripts/install_extras.sh rmse
bash scripts/install_extras.sh plots --force
bash scripts/install_extras.sh streamlit
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
先准备 ERA5 输入（首次机器必须）：
```bash
bash scripts/prepare_era5_inputs.sh
```
如果 `~/.cdsapirc` 缺失且外网不可达：先手工放置原始 nc 或预处理 npy（见下方故障排查第 3 条），再执行该命令。

再跑 GPU smoke：
```bash
bash scripts/run_day3_smoke_gpu.sh
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

## S6 RMSE + Paper 图
推荐：
```bash
bash scripts/final_verify.sh
```

仅重跑该阶段（高级用法）：
```bash
bash scripts/internal/run_day5_rmse.sh --force
bash scripts/internal/run_day6_plots.sh --force
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
```bash
bash scripts/verify_repo_health.sh
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```
通过标准：输出 `FINAL VERIFY PASS`。

## 常见故障排查
1. `CUDAExecutionProvider missing`
```bash
bash scripts/create_gpu_venv.sh --update
source scripts/env_gpu.sh
```

2. `out_dir exists`
- 加 `--force`，或指定新的 `--out-dir`。

3. `missing surface.npy / pressure.npy`
```bash
bash scripts/prepare_era5_inputs.sh
```
若网络不可用，可手工放置其一后再重跑该命令：
- 原始 nc：`$ERA5_RAW_ROOT/era5_single_${DATE}${HOUR}.nc`、`$ERA5_RAW_ROOT/era5_pressure_${DATE}${HOUR}.nc`
- 或预处理 npy：`$PROCESSED_ROOT/surface.npy`、`$PROCESSED_ROOT/pressure.npy`
交互式终端下，脚本也支持直接录入 CDS API Key 并自动写入 `~/.cdsapirc`。
（支持 `key` 或 `uid:key` 两种格式）

4. 360h OOM
```bash
bash scripts/run_360h_split.sh --auto-retry
```

5. `blueprint unavailable (No module named 'cmaps')`
```bash
source scripts/env_gpu.sh
scripts/run_gpu.sh -m pip install -U cmaps pandas xarray
```

6. Streamlit 外网 503
- 使用 SSH 隧道，浏览器访问 `http://127.0.0.1:8501`。

7. `git pull/fetch` TLS 中断（AutoDL 常见）
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
