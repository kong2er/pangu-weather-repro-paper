# 官方入口脚本（复现人员只看这里）

中文说明：
- `scripts/` 仅保留主线入口（S1-S8）。
- `scripts/internal/` 为研发与过程脚本，不在 README 主流程中直接使用。
- 历史脚本在 `tools/legacy/`，仅用于追溯。

公开入口（14 个）：
1. `create_cpu_venv.sh`
2. `create_gpu_venv.sh`
3. `env_cpu.sh`
4. `env_gpu.sh`
5. `run_cpu.sh`
6. `run_gpu.sh`
7. `install_extras.sh`
8. `prepare_era5_inputs.sh`
9. `run_360h_split.sh`
10. `run_product_all.sh`
11. `run_streamlit.sh`
12. `verify_repo_health.sh`
13. `final_verify.sh`
14. `one_shot_verify.sh`
