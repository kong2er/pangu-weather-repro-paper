#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_day3_smoke_gpu.sh"
  echo "Purpose: run Day3 GPU smoke (24h) using run_gpu.sh."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/configs/default.env"
"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/run_smoke_gpu_noarena.py" --step 24
