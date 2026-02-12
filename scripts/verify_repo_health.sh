#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "[FAIL] $1"
  if [[ $# -ge 2 ]]; then
    echo "[NEXT] $2"
  fi
  exit 1
}

[[ -x "$ROOT_DIR/scripts/run_cpu.sh" ]] || fail "missing scripts/run_cpu.sh" "bash scripts/create_cpu_venv.sh"

if [[ ! -x "$ROOT_DIR/.venv-cpu/bin/python" ]]; then
  fail "CPU venv not found" "bash scripts/create_cpu_venv.sh"
fi

echo "[STEP] repo health verify (lightweight)"
echo "[ENV] cpu=$ROOT_DIR/.venv-cpu/bin/python"

echo "[CHECK] import package"
"$ROOT_DIR/scripts/run_cpu.sh" -c "import pangu_weather_repro; print('import ok')"

echo "[CHECK] entry --help"
bash "$ROOT_DIR/scripts/run_product_bundle.sh" --help >/dev/null
bash "$ROOT_DIR/scripts/run_streamlit.sh" --help >/dev/null

echo "[CHECK] targeted tests"
"$ROOT_DIR/scripts/run_cpu.sh" -m pytest -q \
  tests/test_cli_help.py \
  tests/test_manifest_or_paths.py \
  tests/test_plot_filters.py \
  tests/test_run_smoke_help_outside_cwd.py

echo "[CHECK] repo contract health"
"$ROOT_DIR/scripts/run_cpu.sh" tools/check_repo_health.py

echo "[PASS] verify_repo_health"
echo "[NEXT] bash scripts/final_verify.sh --with-e-stage"
