#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv-cpu"
PY="$VENV_DIR/bin/python"

if [[ ! -x "$PY" ]]; then
  echo "ERROR: CPU venv not found: $PY" >&2
  echo "Run: bash scripts/create_cpu_venv.sh" >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR"
exec "$PY" "$@"
