# Release Notes

## v1.0 (2026-02-10)

### Highlights
- Stable CPU/GPU environment split with non-destructive setup.
- Minimal Day3Day6 GPU chain validated via `scripts/regression_minimal.sh`.
- One-command final verification via `scripts/final_verify.sh`.

### What Works End-to-End
- Day8 CPU smoke: `source scripts/env_cpu.sh && python -m pangu_weather_repro.smoke`
- Day3Day6 GPU minimal chain: `source scripts/env_gpu.sh && source configs/default.env && bash scripts/regression_minimal.sh`
- Final verification: `bash scripts/final_verify.sh`

### Outputs Produced
- `artifacts/day5/rmse.csv`
- `figures/day6/field_z500_*_t+024.png`
- `figures/day6/field_z500_*_t+030.png`
- `figures/day6/rmse_z500_*.png`
- `artifacts/day7/REPORT.md`

### Troubleshooting Shortcuts
- CPU venv missing: `bash scripts/create_cpu_venv.sh`
- CPU update: `bash scripts/create_cpu_venv.sh --update`
- GPU provider missing: `bash scripts/install_gpu_deps.sh && source scripts/env_gpu.sh`
- netCDF4 missing: `bash scripts/install_extras.sh rmse`
- matplotlib missing: `bash scripts/install_extras.sh plots`

