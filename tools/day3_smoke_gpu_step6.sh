#!/usr/bin/env bash
set -euo pipefail

# 取脚本真实路径（兼容被 source / 相对路径 / 软链接）
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

set -a
source "$PROJECT_ROOT/configs/default.env"
set +a

export UV_NO_SYNC=1
export MODEL_PATH="${MODELS_ROOT}/pangu_weather_6.onnx"

# load CUDA12 wheels env if you created it
test -f "$PROJECT_ROOT/tools/enable_cuda12_runtime_env.sh" && source "$PROJECT_ROOT/tools/enable_cuda12_runtime_env.sh"

export ORT_CUDA_ENABLE_ARENA=0
export ORT_CUDA_ALLOCATOR=cuda_malloc_async
export ORT_CUDNN_ALGO_SEARCH=DEFAULT
export ORT_INTRA_OP=1
export ORT_INTER_OP=1

CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}" uv run python "$PROJECT_ROOT/tools/run_smoke_gpu_noarena.py" --step 6

echo "[OK] report => ${OUTPUT_ROOT}/smoke_6h_report.json"
