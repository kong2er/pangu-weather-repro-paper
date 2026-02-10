#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_cpu.sh <python-args>"
  echo "Examples:"
  echo "  scripts/run_cpu.sh -m pangu_weather_repro.smoke"
  echo "  scripts/run_cpu.sh -c \"import sys; print(sys.executable)\""
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv-cpu"
PY="$VENV_DIR/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "ERROR: CPU venv not found: $PY" >&2
  echo "Run: bash scripts/create_cpu_venv.sh" >&2
  exit 1
fi

if [[ "$#" -lt 1 ]]; then
  echo "No command provided. Try: scripts/run_cpu.sh --help" >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR"
exec "$PY" "$@"
