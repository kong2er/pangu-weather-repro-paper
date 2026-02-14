#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WITH_E_STAGE=0
E_STAGE_FORCE=0

usage() {
  cat <<'EOF'
Usage: bash scripts/final_verify.sh [--with-e-stage] [--e-stage-force]

Options:
  --with-e-stage   Also run E-stage verify (Streamlit/product checks).
  --e-stage-force  Pass --force to scripts/internal/run_e_stage_verify.sh (requires --with-e-stage).
  -h, --help       Show this help message.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-e-stage)
      WITH_E_STAGE=1
      shift
      ;;
    --e-stage-force)
      E_STAGE_FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$E_STAGE_FORCE" -eq 1 && "$WITH_E_STAGE" -ne 1 ]]; then
  echo "ERROR: --e-stage-force requires --with-e-stage" >&2
  exit 2
fi

fail() {
  echo "ERROR: $1" >&2
  exit "${2:-1}"
}

if [[ ! -x "$ROOT_DIR/scripts/internal/run_day8_cpu_smoke.sh" ]]; then
  fail "missing scripts/internal/run_day8_cpu_smoke.sh; run: git pull --rebase" 1
fi

if [[ ! -f "$ROOT_DIR/configs/default.env" ]]; then
  fail "missing configs/default.env; create it or copy template" 1
fi

echo "== CPU smoke =="
bash "$ROOT_DIR/scripts/internal/run_day8_cpu_smoke.sh"

echo "== Load GPU env =="
source "$ROOT_DIR/configs/default.env"

echo "== Day3 smoke =="
bash "$ROOT_DIR/scripts/internal/run_day3_smoke_gpu.sh"

echo "== Day5 rmse =="
bash "$ROOT_DIR/scripts/internal/run_day5_rmse.sh"

echo "== Day6 plots =="
bash "$ROOT_DIR/scripts/internal/run_day6_plots.sh"

# artifacts check
[[ -f "$ROOT_DIR/artifacts/day5/rmse.csv" ]] || fail "missing artifacts/day5/rmse.csv; run: bash scripts/internal/run_day5_rmse.sh" 2
ls -1 "$ROOT_DIR/figures/day6"/*.png >/dev/null 2>&1 || fail "missing figures/day6/*.png; run: bash scripts/internal/run_day6_plots.sh" 2

# providers check
if [[ -x "$ROOT_DIR/scripts/run_cpu.sh" ]]; then
  echo "== CPU providers =="
  "$ROOT_DIR/scripts/run_cpu.sh" - <<'PY' || true
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

if [[ "$WITH_E_STAGE" -eq 1 ]]; then
  [[ -f "$ROOT_DIR/scripts/internal/run_e_stage_verify.sh" ]] || fail "missing scripts/internal/run_e_stage_verify.sh; run: git pull --rebase" 2
  echo "== E-stage verify =="
  if [[ "$E_STAGE_FORCE" -eq 1 ]]; then
    bash "$ROOT_DIR/scripts/internal/run_e_stage_verify.sh" --force
  else
    bash "$ROOT_DIR/scripts/internal/run_e_stage_verify.sh"
  fi
  [[ -f "$ROOT_DIR/artifacts/day7/E_STAGE_REPORT.md" ]] || fail "missing artifacts/day7/E_STAGE_REPORT.md; run: bash scripts/internal/run_e_stage_verify.sh --force" 2
fi

echo "FINAL VERIFY PASS"
