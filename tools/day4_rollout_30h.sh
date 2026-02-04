#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BASH_SOURCE[0]:-}" ]]; then
  echo "This script must be run with bash." >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

set -a
source "${ROOT_DIR}/configs/default.env"
set +a

export ORT_CUDA_ENABLE_ARENA="${ORT_CUDA_ENABLE_ARENA:-0}"
export ORT_CUDA_ALLOCATOR="${ORT_CUDA_ALLOCATOR:-cuda_malloc_async}"
export ORT_CUDNN_ALGO_SEARCH="${ORT_CUDNN_ALGO_SEARCH:-DEFAULT}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"

uv run python tools/day4_rollout.py \
  --steps 24,6 \
  --noarena \
  --out-dir "${OUTPUT_ROOT}/day4_rollout_30h" \
  "$@"
