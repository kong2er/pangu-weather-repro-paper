#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_alignment_experiments.sh [--out FILE] [--force]"
  echo "Purpose: record alignment runs for 1/3/6/24h + 1–84h + 84–360h (dry-run)."
  echo "Default: no overwrite, writes to artifacts/day7/alignment_experiments.md"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_FILE="${ROOT_DIR}/artifacts/day7/alignment_experiments.md"
FORCE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      OUT_FILE="$2"
      shift 2
      ;;
    --force)
      FORCE="1"
      shift 1
      ;;
    *)
      echo "Unknown arg: $1"
      exit 1
      ;;
  esac
done

if [[ -f "${OUT_FILE}" && -z "${FORCE}" ]]; then
  echo "Report exists (skip): ${OUT_FILE}"
  echo "Use --force to overwrite."
  exit 0
fi

mkdir -p "$(dirname "${OUT_FILE}")"

{
  echo "# Alignment Experiments (Inference)"
  echo ""
  echo "## 环境"
  echo "- GPU：\`${ROOT_DIR}/.venv-gpu\`"
  echo "- 依赖：models 已下载、processed 已准备"
  echo ""
  echo "## 1/3/6/24h 单步推理验证（short mode）"
  echo '```bash'
  echo 'scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --short-step 1 --target-hours 24'
  echo 'scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --short-step 3 --target-hours 24'
  echo 'scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --short-step 6 --target-hours 24'
  echo 'scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --short-step 24 --target-hours 24'
  echo '```'
  echo ""
  echo "## 1–84h 逐小时（short mode）"
  echo '```bash'
  echo 'scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --short-step 1 --target-hours 84'
  echo '```'
  echo ""
  echo "## 84–360h 迭代（dry-run 计划）"
  echo '```bash'
  echo 'scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode full --short-step 1 --long-step 24 --target-hours 360 --dry-run'
  echo '```'
  echo ""
  echo "## 稳定跑法（推荐）"
  echo '```bash'
  echo 'scripts/run_360h_split.sh --auto-retry'
  echo '```'
  echo ""
  echo "## 说明"
  echo "- 默认不覆盖产物；需要覆盖请加 --force。"
  echo "- 如遇 OOM，优先使用 split + auto-retry。"
} > "${OUT_FILE}"

echo "Wrote ${OUT_FILE}"
