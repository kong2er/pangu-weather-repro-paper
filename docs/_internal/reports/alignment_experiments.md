# Alignment Experiments (Inference)

## 环境
- GPU：`/root/projects/pangu-weather-repro-uv/.venv-gpu`
- 依赖：models 已下载、processed 已准备

## 1/3/6/24h 单步推理验证（short mode）
```bash
scripts/run_gpu.sh tools/run_forecast.py --strategy pangu_ref --mode short --short-step 1 --target-hours 24
scripts/run_gpu.sh tools/run_forecast.py --strategy pangu_ref --mode short --short-step 3 --target-hours 24
scripts/run_gpu.sh tools/run_forecast.py --strategy pangu_ref --mode short --short-step 6 --target-hours 24
scripts/run_gpu.sh tools/run_forecast.py --strategy pangu_ref --mode short --short-step 24 --target-hours 24
```

## 1–84h 逐小时（short mode）
```bash
scripts/run_gpu.sh tools/run_forecast.py --strategy pangu_ref --mode short --short-step 1 --target-hours 84
```

## 84–360h 迭代（dry-run 计划）
```bash
scripts/run_gpu.sh tools/run_forecast.py --strategy pangu_ref --mode full --short-step 1 --long-step 24 --target-hours 360 --dry-run
```

## 稳定跑法（推荐）
```bash
scripts/run_360h_split.sh --auto-retry
```

## 说明
- 默认不覆盖产物；需要覆盖请加 --force。
- 如遇 OOM，优先使用 split + auto-retry。
