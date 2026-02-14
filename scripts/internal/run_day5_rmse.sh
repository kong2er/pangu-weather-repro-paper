#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: scripts/internal/run_day5_rmse.sh [--force]
Purpose: 计算 Day5 z500 RMSE 并生成 CSV。

前置条件:
  1) eval_z500.npz 存在（由 Day4 rollout 生成）
  2) ERA5 真值文件存在（或 npz 中包含 gt_z500）

如果真值文件缺失:
  bash scripts/prepare_era5_inputs.sh --ensure-eval-gt --yes
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="${1:-}"
source "${ROOT_DIR}/configs/default.env"

OUT_CSV="${ROOT_DIR}/artifacts/day5/rmse.csv"
PRED_NPZ="${OUTPUT_ROOT}/day4_rollout_30h/eval_z500.npz"
META_JSON="${OUTPUT_ROOT}/day4_rollout_30h/eval_z500_meta.json"
mkdir -p "${ROOT_DIR}/artifacts/day5"

echo "[STEP] Day5 RMSE"
echo "[ENV] GPU (.venv-gpu)"
echo "[INPUT] ${PRED_NPZ}"
echo "[OUTPUT] ${OUT_CSV}"
echo "[NEXT] scripts/internal/run_day6_plots.sh"

if [[ ! -f "${PRED_NPZ}" ]]; then
  echo "[FAIL] 缺少评估包: ${PRED_NPZ}"
  echo "[原因] Day4 rollout 尚未完成"
  echo "[修复] scripts/run_gpu.sh tools/day4_rollout.py --steps 24,6 --noarena --out-dir \"${OUTPUT_ROOT}/day4_rollout_30h\""
  exit 2
fi

# ---------------------------------------------------------------------------
# 检查 ERA5 真值文件是否就绪
# 优先检查 npz 中是否已有 gt_z500；若无，则检查 meta 中的 gt_paths
# ---------------------------------------------------------------------------
GT_CHECK_OK=1
GT_CHECK_MSG=""
if "${ROOT_DIR}/scripts/run_gpu.sh" -c "
import numpy as np, sys, json, os
npz = np.load('${PRED_NPZ}')
if 'gt_z500' in npz:
    sys.exit(0)  # gt 内嵌在 npz 中，无需外部文件
meta_path = '${META_JSON}'
if not os.path.exists(meta_path):
    print('meta_json_missing')
    sys.exit(1)
with open(meta_path) as f:
    meta = json.load(f)
gt_paths = meta.get('gt_paths', [])
missing = [p for p in gt_paths if not os.path.exists(p)]
if missing:
    for m in missing:
        print(m)
    sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
  echo "[OK] ERA5 真值文件检查通过"
else
  GT_MISSING=$("${ROOT_DIR}/scripts/run_gpu.sh" -c "
import numpy as np, json, os, sys
npz = np.load('${PRED_NPZ}')
if 'gt_z500' in npz:
    sys.exit(0)
meta_path = '${META_JSON}'
if not os.path.exists(meta_path):
    print('meta_json_missing: ${META_JSON}')
    sys.exit(0)
with open(meta_path) as f:
    meta = json.load(f)
for p in meta.get('gt_paths', []):
    if not os.path.exists(p):
        print(p)
" 2>/dev/null || true)

  if [[ -n "${GT_MISSING}" ]]; then
    echo "[WARN] 缺少 ERA5 真值文件:"
    echo "${GT_MISSING}" | while IFS= read -r line; do
      echo "  - ${line}"
    done
    echo ""
    echo "[说明] RMSE 评估需要这些真值文件用于对比。"
    echo "[修复] bash scripts/prepare_era5_inputs.sh --ensure-eval-gt --yes"
    echo "[备选] 手动放置以上文件到 ${ERA5_RAW_ROOT}/"
    echo ""
    echo "[继续] 仍尝试运行 RMSE（可能使用 npz 内嵌 gt 或报错）..."
  fi
fi

if [[ -f "${OUT_CSV}" && "${MODE}" != "--force" ]]; then
  echo "[跳过] rmse.csv 已存在。使用 --force 覆盖。"
  head -n 3 "${OUT_CSV}"
  exit 0
fi

"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/eval_rmse.py" \
  --pred "${PRED_NPZ}" \
  --var z500 \
  --out "${OUT_CSV}"

echo ""
echo "[验收] 检查产物..."
if [[ -f "${OUT_CSV}" && -s "${OUT_CSV}" ]]; then
  echo "[PASS] rmse.csv 生成成功"
  head -n 3 "${OUT_CSV}"
else
  echo "[FAIL] rmse.csv 为空或不存在"
  exit 2
fi
