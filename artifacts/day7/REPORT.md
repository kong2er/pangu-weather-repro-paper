# REPORT (Day3–Day8 Stable Repro + Alignment Progress)

## Environment
- CPU smoke: `scripts/run_day8_cpu_smoke.sh`
- GPU regression: `scripts/run_day3_smoke_gpu.sh` → `scripts/run_day5_rmse.sh` → `scripts/run_day6_plots.sh`

## Stable Chain (commands)
1) scripts/run_day8_cpu_smoke.sh
2) scripts/run_day3_smoke_gpu.sh
3) scripts/run_day5_rmse.sh
4) scripts/run_day6_plots.sh
5) scripts/final_verify.sh

## Expected Artifacts
- artifacts/day5/rmse.csv
- figures/day6/field_z500_2023070900_t+024.png
- figures/day6/field_z500_2023070900_t+030.png
- figures/day6/rmse_z500_2023070900.png
- artifacts/day7/reference_diff_report.md

## Stability Improvements (Completed)
- CPU/GPU venv creation is idempotent with --update/--force
- run_cpu.sh / run_gpu.sh enforce correct interpreter and PYTHONPATH
- env_cpu.sh clears CUDA paths; env_gpu.sh validates CUDA libs + providers
- Day5/Day6 scripts are non-destructive by default; --force to overwrite
- Unified dependency hints via scripts/install_extras.sh

## Alignment Progress (zjobsdev/pangu)
- Added short/long schedule builder (1–84h / 84–360h) and unified runner
- Added tools/run_forecast.py for 1/3/6/24h model selection
- Added paper bundle plotting with metadata JSON
- Added RegionDatasetAdapter + region demo crop

## Changed Files (Key)
- pangu_weather_repro/infer/*
- pangu_weather_repro/region/*
- tools/run_forecast.py
- tools/plot_paper_bundle.py
- tools/region_demo.py
- tools/plot_fields.py
- scripts/create_cpu_venv.sh
- scripts/create_gpu_venv.sh
- scripts/env_cpu.sh
- scripts/env_gpu.sh
- scripts/run_cpu.sh
- scripts/run_gpu.sh
- scripts/run_day3_smoke_gpu.sh
- scripts/run_day5_rmse.sh
- scripts/run_day6_plots.sh
- scripts/run_day8_cpu_smoke.sh
- scripts/final_verify.sh
- scripts/install_gpu_deps.sh
- scripts/install_extras.sh
- scripts/vendor_sync_reference.sh
- docs/GAP_REPORT.md
- docs/reference_pangu.md
- README.md
- RUNBOOK.md
