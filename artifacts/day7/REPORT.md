# REPORT (Day3->Day6 Minimal Chain)

## Environment
- python: /root/projects/pangu-weather-repro-uv/.venv-gpu/bin/python
- onnxruntime providers: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']

## Minimal Chain (commands)
1) scripts/run_day3_smoke_gpu.sh
2) scripts/run_day5_rmse.sh
3) scripts/run_day6_plots.sh
4) scripts/regression_minimal.sh

## Expected Artifacts
- artifacts/day5/rmse.csv
- figures/day6/field_z500_2023070900_t+024.png
- figures/day6/field_z500_2023070900_t+030.png
- figures/day6/rmse_z500_2023070900.png

## Covered Pitfalls
- PYTHONPATH missing in run_smoke_gpu_noarena
- LD_LIBRARY_PATH missing for CUDA libs
- pip logging error (.venv-gpu/bin/pip missing)
- missing netCDF4/cdsapi/matplotlib/cartopy
- plot_fields default rollout/lead mismatch

## Changed Files
- scripts/run_gpu.sh
- scripts/fix_venv_pip.sh
- scripts/install_gpu_deps.sh
- scripts/install_extras.sh
- scripts/run_day3_smoke_gpu.sh
- scripts/run_day5_rmse.sh
- scripts/run_day6_plots.sh
- scripts/regression_minimal.sh
- tools/run_smoke_gpu_noarena.py
- tools/eval_rmse.py
- tools/plot_fields.py
- tools/plot_rmse_curve.py
- tests/test_plot_fields_validation.py
- .github/workflows/ci.yml
- README.md
