#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

fail() {
  echo "ERROR: $1" >&2
  exit "${2:-1}"
}

if [[ ! -x "$ROOT_DIR/scripts/run_day8_cpu_smoke.sh" ]]; then
  fail "missing scripts/run_day8_cpu_smoke.sh; run: chmod +x scripts/run_day8_cpu_smoke.sh" 1
fi

if [[ ! -f "$ROOT_DIR/configs/default.env" ]]; then
  fail "missing configs/default.env; create it or copy template" 1
fi

echo "== CPU smoke =="
bash "$ROOT_DIR/scripts/run_day8_cpu_smoke.sh"

echo "== GPU regression =="
bash "$ROOT_DIR/scripts/regression_minimal.sh"

# artifacts check
[[ -f "$ROOT_DIR/artifacts/day5/rmse.csv" ]] || fail "missing artifacts/day5/rmse.csv; run: scripts/run_day5_rmse.sh or scripts/regression_minimal.sh" 2
ls -1 "$ROOT_DIR/figures/day6"/*.png >/dev/null 2>&1 || fail "missing figures/day6/*.png; run: scripts/run_day6_plots.sh or scripts/regression_minimal.sh" 2

# providers check
if [[ -x "$ROOT_DIR/scripts/run_cpu.sh" ]]; then
  echo "== CPU providers =="
  "$ROOT_DIR/scripts/run_cpu.sh" -c "import importlib.util; spec=importlib.util.find_spec('onnxruntime');\nprint('onnxruntime in CPU env:', bool(spec));\nprint('providers:', __import__('onnxruntime').get_available_providers() if spec else 'N/A')"
else
  echo "WARN: scripts/run_cpu.sh not found; skipping CPU providers"
fi

if [[ -x "$ROOT_DIR/scripts/run_gpu.sh" ]]; then
  echo "== GPU providers =="
  "$ROOT_DIR/scripts/run_gpu.sh" -c "import onnxruntime as ort; print('providers:', ort.get_available_providers())"
  "$ROOT_DIR/scripts/run_gpu.sh" -c "import onnxruntime as ort; assert 'CUDAExecutionProvider' in ort.get_available_providers(), 'CUDAExecutionProvider missing'"
else
  fail "missing scripts/run_gpu.sh" 2
fi

echo "FINAL VERIFY PASS"
