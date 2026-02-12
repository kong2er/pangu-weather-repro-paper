# ENTRYPOINT MATRIX（入口分层矩阵）

中文说明：
- 复现人员优先使用“官方入口”。
- “高级入口”用于可选扩展能力或精细控制。
- “归档入口”仅用于历史追溯，不建议纳入标准流程。

## A. 官方入口（推荐）
- 环境：`scripts/create_cpu_venv.sh`、`scripts/create_gpu_venv.sh`、`scripts/env_cpu.sh`、`scripts/env_gpu.sh`
- 健康检查：`scripts/verify_repo_health.sh`
- 最终验收：`scripts/final_verify.sh`
- 推理：`scripts/run_360h_split.sh`（优先）、`scripts/run_360h_full.sh`
- 阶段链路：`scripts/run_day3_smoke_gpu.sh`、`scripts/run_day5_rmse.sh`、`scripts/run_day6_plots.sh`、`scripts/run_day8_cpu_smoke.sh`
- 产品图族：`scripts/run_product_all.sh`、`scripts/run_product_bundle.sh`
- 对齐报告：`scripts/run_alignment_experiments.sh`、`scripts/run_e_stage_verify.sh`、`scripts/gen_report.sh`

## B. 高级入口（按需）
- 预测主 CLI：`tools/run_forecast.py`
- 产品图工具：`tools/plot_product_bundle.py`
- 论文图工具：`tools/plot_paper_bundle.py`
- Region demo：`tools/region_demo.py`
- 评估工具：`tools/eval_rmse.py`

## C. 归档入口（历史/调试，不推荐）
- `tools/legacy/day4_rollout_codex.py`
- `tools/legacy/day3_smoke_gpu_step6.sh`
- `tools/legacy/day4_infer_onnx.py`
- `tools/legacy/cds_smoke_t2m.py`

## 使用规则
1. 新增复现流程请先在官方入口脚本封装，再调用 `tools/`。
2. 不在 README 主流程中暴露 `tools/legacy/`。
3. 标准故障排查优先看脚本的 `[NEXT]` 提示。
