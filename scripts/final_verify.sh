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

echo "== Load GPU env =="
source "$ROOT_DIR/configs/default.env"

echo "== Day3 smoke =="
bash "$ROOT_DIR/scripts/run_day3_smoke_gpu.sh"

echo "== Day5 rmse =="
bash "$ROOT_DIR/scripts/run_day5_rmse.sh"

echo "== Day6 plots =="
bash "$ROOT_DIR/scripts/run_day6_plots.sh"

# artifacts check
[[ -f "$ROOT_DIR/artifacts/day5/rmse.csv" ]] || fail "missing artifacts/day5/rmse.csv; run: scripts/run_day5_rmse.sh or scripts/regression_minimal.sh" 2
ls -1 "$ROOT_DIR/figures/day6"/*.png >/dev/null 2>&1 || fail "missing figures/day6/*.png; run: scripts/run_day6_plots.sh or scripts/regression_minimal.sh" 2

# providers check
if [[ -x "$ROOT_DIR/scripts/run_cpu.sh" ]]; then
  echo "== CPU providers =="
  "$ROOT_DIR/scripts/run_cpu.sh" - <<'PY'
import importlib.util
spec = importlib.util.find_spec("onnxruntime")
print("onnxruntime in CPU env:", bool(spec))
if spec:
  import onnxruntime as ort
  print("providers:", ort.get_available_providers())
else:
  print("providers:", "N/A")
PY
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
