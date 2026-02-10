#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_day8_cpu_smoke.sh"
  echo "Purpose: run Day8 CPU smoke."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x "$ROOT_DIR/scripts/run_cpu.sh" ]]; then
  echo "ERROR: missing scripts/run_cpu.sh; run: chmod +x scripts/run_cpu.sh" >&2
  exit 1
fi

echo "[STEP] Day8 CPU smoke"
echo "[ENV] CPU (.venv-cpu)"
echo "[OUTPUT] contracts smoke ok"
if ! "$ROOT_DIR/scripts/run_cpu.sh" -m pangu_weather_repro.smoke; then
  echo "CPU smoke failed" >&2
  echo "python: $(command -v python || true)" >&2
  echo "python -V: $(python -V 2>&1 || true)" >&2
  echo "Next: bash scripts/create_cpu_venv.sh" >&2
  exit 1
fi
