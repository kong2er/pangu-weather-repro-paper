# REPO SANITIZE DELIVERY（仓库治理交付清单）

## 1) 移动/重命名/删除清单

### 产物清理（取消跟踪，不删本地）
- `artifacts/day5/rmse.csv`（git tracked -> untracked）
- `artifacts/day7/metrics_summary.csv`（git tracked -> untracked）
- `figures/day6/field_z500_2023070900_t+024.png`（git tracked -> untracked）
- `figures/day6/rmse_z500_2023070900.png`（git tracked -> untracked）
- `figures/day7/summary_acc.png`（git tracked -> untracked）
- `figures/day7/summary_rmse.png`（git tracked -> untracked）

### 脚本归类
- `tools/day4_rollout_codex.py` -> `tools/legacy/day4_rollout_codex.py`
- `tools/day3_smoke_gpu_step6.sh` -> `tools/legacy/day3_smoke_gpu_step6.sh`
- `scripts/day4_infer_onnx.py` -> `tools/legacy/day4_infer_onnx.py`
- `scripts/cds_smoke_t2m.py` -> `tools/legacy/cds_smoke_t2m.py`
- 新增：`scripts/README.md`（官方入口清单）
- 新增：`scripts/verify_repo_health.sh`（轻量健康验收）

### 文档归类
- 新增：`docs/REPO_SANITIZE_PLAN.md`
- 新增：`docs/DELIVERY_SUMMARY.md`
- 新增：`docs/REPO_SANITIZE_DELIVERY.md`

### 代码归类
- 无核心算法变更（仅入口/治理层改动）。

## 2) 新目录树（2~3 层）
```text
pangu_weather_repro/
  app/
  infer/
  region/
  visualization/
scripts/
  README.md
  final_verify.sh
  run_360h_split.sh
  run_product_all.sh
  run_e_stage_verify.sh
  verify_repo_health.sh
  ...
tools/
  plot_product_bundle.py
  run_forecast.py
  ...
  legacy/
    day4_rollout_codex.py
    day3_smoke_gpu_step6.sh
    day4_infer_onnx.py
    cds_smoke_t2m.py
docs/
  DELIVERY_SUMMARY.md
  REPO_SANITIZE_PLAN.md
  REPO_SANITIZE_DELIVERY.md
artifacts/
  day4/.gitkeep
  day7/*.md
figures/
  .gitkeep
  README.md
outputs/
  .gitkeep
  README.md
```

## 3) 8 阶段复现命令表
- S1 环境与依赖：`bash scripts/create_cpu_venv.sh && bash scripts/create_gpu_venv.sh`
  - 产物：`.venv-cpu/`、`.venv-gpu/`
  - 验收：`source scripts/env_gpu.sh` 有 `CUDAExecutionProvider`
- S2 CPU smoke：`bash scripts/run_day8_cpu_smoke.sh`
  - 产物：终端 `contracts smoke ok`
  - 验收：退出码 0
- S3 GPU smoke：`bash scripts/run_day3_smoke_gpu.sh`
  - 产物：`$OUTPUT_ROOT/smoke_24h_report.json`
  - 验收：providers 含 CUDA
- S4 84h 推理：`scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --target-hours 84 --noarena --threads 1 --out-dir "$OUTPUT_ROOT/forecast_84h_$(date +%Y%m%d_%H%M%S)"`
  - 产物：`forecast_report.json`
  - 验收：报告存在
- S5 360h 推理：`bash scripts/run_360h_split.sh --auto-retry`
  - 产物：`forecast_360h_split_*_84h/forecast_report.json` 与 `*_276h/forecast_report.json`
  - 验收：终端出现 long report / retry success
- S6 RMSE + paper 图：`bash scripts/run_day5_rmse.sh && bash scripts/run_day6_plots.sh`
  - 产物：`artifacts/day5/rmse.csv`、`figures/day6/*.png`
  - 验收：文件存在且非空
- S7 产品图族 + Streamlit：`bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force && bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501`
  - 产物：`figures/product/*.png`、`figures/product/*.json`
  - 验收：`bash scripts/run_e_stage_verify.sh --force`
- S8 最终验收：`bash scripts/verify_repo_health.sh && bash scripts/final_verify.sh --with-e-stage --e-stage-force && bash scripts/gen_report.sh`
  - 产物：`artifacts/day7/REPORT.md`、`artifacts/day7/E_STAGE_REPORT.md`
  - 验收：`FINAL VERIFY PASS`

## 4) 复现人员最短路径（<=10 行）
```bash
bash scripts/create_cpu_venv.sh
bash scripts/create_gpu_venv.sh
source configs/default.env
bash scripts/run_day8_cpu_smoke.sh
bash scripts/run_day3_smoke_gpu.sh
bash scripts/run_360h_split.sh --auto-retry
bash scripts/run_day5_rmse.sh
bash scripts/run_day6_plots.sh
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```

## 5) 建议的 git 提交记录摘要
- `chore: stop tracking runtime artifacts and add repo sanitize plan`
- `chore: archive unused experimental scripts under tools/legacy`
- `chore: mark official script entrypoints and archive debug scripts`
- `chore: add lightweight repo health verification entrypoint`
- `docs: add 8-stage reproducibility delivery summary`
- `docs: add final repo sanitize delivery checklist`
