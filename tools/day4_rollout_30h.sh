#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

set -a
source "$PROJECT_ROOT/configs/default.env"
set +a

export UV_NO_SYNC=1

OUT="$OUTPUT_ROOT/day4_rollout_30h"
mkdir -p "$OUT"

CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" uv run python tools/day4_rollout.py \
  --schedule 24 6 \
  --models-root "$MODELS_ROOT" \
  --output-dir "$OUT"

echo "[OK] 30h rollout => $OUT"
