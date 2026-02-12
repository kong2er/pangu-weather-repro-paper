# 官方入口脚本（复现人员只看这里）

中文说明：
- `scripts/` 目录仅保留阶段化复现入口。
- 历史调试/实验脚本已归档到 `tools/legacy/`，不建议直接用于标准复现。
- 入口分层矩阵见：`docs/ENTRYPOINT_MATRIX.md`

推荐阶段入口：
1. 环境：`create_cpu_venv.sh` / `create_gpu_venv.sh` / `env_cpu.sh` / `env_gpu.sh`
2. 主链验收：`final_verify.sh`
3. 推理：`run_360h_split.sh` / `run_360h_full.sh`
4. 图族：`run_product_bundle.sh` / `run_product_all.sh`
5. 对齐与报告：`run_alignment_experiments.sh` / `run_e_stage_verify.sh` / `gen_report.sh`
