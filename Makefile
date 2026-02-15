SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

ROLL_STEPS_6H := 6
ROLL_STEPS_30H := 24,6
ROLL_STEPS_360H := 24,24,24,24,24,24,24,24,24,24,24,24,24,24,24

.PHONY: env env-cpu env-gpu models era5-0900 era5-0906 preprocess rollout-6h rollout-30h rollout-360h day7 day8 smoke smoke-runtime check

env:
	uv venv --python 3.10
	uv sync

env-cpu:
	uv venv --python 3.10 .venv-cpu
	UV_VENV=.venv-cpu uv sync

env-gpu:
	uv venv --python 3.10 .venv-gpu
	UV_VENV=.venv-gpu uv sync --extra gpu

models:
	bash scripts/internal/01_download_models.sh

era5-0900:
	source configs/default.env
	uv run python scripts/internal/03_download_era5_single.py --date 20230709 --hour 00
	uv run python scripts/internal/03_download_era5_pressure.py --date 20230709 --hour 00

era5-0906:
	source configs/default.env
	uv run python scripts/internal/03_download_era5_single.py --date 20230709 --hour 06
	uv run python scripts/internal/03_download_era5_pressure.py --date 20230709 --hour 06

preprocess:
	source configs/default.env
	uv run python scripts/internal/04_preprocess_era5_to_npy.py --date 20230709 --hour 00
	uv run python scripts/internal/05_validate_inputs.py

rollout-6h:
	source configs/default.env
	uv run python tools/day4_rollout.py --steps $(ROLL_STEPS_6H) --noarena --out-dir "$$OUTPUT_ROOT/day4_rollout_06h"

rollout-30h:
	source configs/default.env
	uv run python tools/day4_rollout.py --steps $(ROLL_STEPS_30H) --noarena --out-dir "$$OUTPUT_ROOT/day4_rollout_30h"

rollout-360h:
	source configs/default.env
	uv run python tools/day4_rollout.py --steps $(ROLL_STEPS_360H) --noarena --out-dir "$$OUTPUT_ROOT/day4_rollout_360h"

day7:
	source configs/default.env
	uv run python tools/day7_metrics.py --vars z500,t2m,u10 --leads 6 --out artifacts/day7/metrics_summary.csv --md docs/day7_results.md
	uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric rmse_latw --out figures/day7/summary_rmse.png

day8:
	source configs/default.env
	uv run python tools/day7_metrics.py --vars z500,t2m,u10 --leads 6 --out artifacts/day7/metrics_summary.csv --md docs/day7_results.md
	uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric rmse_latw --out figures/day7/summary_rmse.png
	uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric acc_latw --out figures/day7/summary_acc.png

smoke:
	uv run python -m pangu_weather_repro.smoke
	uv run python tools/check_repo_health.py

smoke-runtime:
	source configs/default.env
	uv run python scripts/internal/05_validate_inputs.py
	uv run python scripts/internal/06_infer_smoke.py --step 6

check:
	uv run python tools/check_repo_health.py
