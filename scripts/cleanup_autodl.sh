#!/usr/bin/env bash
set -euo pipefail

ROOT_TMP_DEFAULT="/root/autodl-tmp/pangu-weather-repro"
OUTPUT_ROOT_DEFAULT="${ROOT_TMP_DEFAULT}/outputs"
MODELS_ROOT_DEFAULT="${ROOT_TMP_DEFAULT}/models"
PROCESSED_ROOT_DEFAULT="${ROOT_TMP_DEFAULT}/processed"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DRY_RUN=1
KEEP_DAYS=3
KEEP_LATEST=2
OUTPUT_ROOT="${OUTPUT_ROOT_DEFAULT}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/cleanup_autodl.sh [--dry-run] [--force] [--keep-days N] [--keep-latest N] [--output-root PATH]

Options:
  --dry-run         仅打印将删除内容（默认）
  --force           真正执行删除
  --keep-days N     保留最近 N 天的 forecast/smoke/split 目录（默认: 3）
  --keep-latest N   额外保留最新 N 个 forecast/smoke/split 目录（默认: 2）
  --output-root P   指定输出目录（默认: /root/autodl-tmp/pangu-weather-repro/outputs）
  -h, --help        显示帮助

Examples:
  bash scripts/cleanup_autodl.sh
  bash scripts/cleanup_autodl.sh --force --keep-latest 2 --keep-days 3
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --force) DRY_RUN=0; shift ;;
    --keep-days) KEEP_DAYS="${2:-}"; shift 2 ;;
    --keep-latest) KEEP_LATEST="${2:-}"; shift 2 ;;
    --output-root) OUTPUT_ROOT="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 2 ;;
  esac
done

if ! [[ "${KEEP_DAYS}" =~ ^[0-9]+$ && "${KEEP_LATEST}" =~ ^[0-9]+$ ]]; then
  echo "keep-days/keep-latest must be non-negative integers"
  exit 2
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[STEP] cleanup mode: DRY-RUN"
else
  echo "[STEP] cleanup mode: FORCE"
fi

echo "[STEP] baseline disk usage"
echo "[INFO] repo_root=${REPO_ROOT}"
echo "[INFO] output_root=${OUTPUT_ROOT}"
echo "[INFO] keep_days=${KEEP_DAYS}, keep_latest=${KEEP_LATEST}"
df -h || true
du -sh "${OUTPUT_ROOT}" 2>/dev/null || true
du -sh "${MODELS_ROOT_DEFAULT}" 2>/dev/null || true
du -sh "${PROCESSED_ROOT_DEFAULT}" 2>/dev/null || true

if [[ ! -d "${OUTPUT_ROOT}" ]]; then
  echo "[WARN] output_root not found: ${OUTPUT_ROOT}"
  echo "[NEXT] source configs/default.env && bash scripts/cleanup_autodl.sh --dry-run"
  exit 0
fi

if [[ "${OUTPUT_ROOT}" == "${MODELS_ROOT_DEFAULT}" || "${OUTPUT_ROOT}" == "${PROCESSED_ROOT_DEFAULT}" ]]; then
  echo "[ERROR] output_root must not point to models/processed"
  exit 2
fi

TMP_LIST="$(mktemp)"
trap 'rm -f "${TMP_LIST}"' EXIT

# 仅匹配可再生成的目录/文件前缀；永远不碰 day4_rollout_30h / models / processed / repo。
while IFS= read -r p; do
  base="$(basename "${p}")"
  if [[ "${base}" =~ ^forecast_ || "${base}" =~ ^smoke_ || "${base}" =~ ^forecast_360h_split_ ]]; then
    if [[ "${base}" == "forecast_84h" || "${base}" == "forecast_360h" ]]; then
      echo "${p}" >> "${TMP_LIST}"
    elif [[ "${base}" == "day4_rollout_30h" ]]; then
      :
    else
      echo "${p}" >> "${TMP_LIST}"
    fi
  fi
done < <(find "${OUTPUT_ROOT}" -mindepth 1 -maxdepth 1 \( -type d -o -type f \) 2>/dev/null | sort)

mapfile -t CANDIDATES < "${TMP_LIST}" || true

declare -a KEEP_SET=()
if ((${#CANDIDATES[@]} > 0)); then
  for p in "${CANDIDATES[@]}"; do
    mtime_epoch="$(stat -c %Y "${p}" 2>/dev/null || echo 0)"
    now_epoch="$(date +%s)"
    age_days="$(( (now_epoch - mtime_epoch) / 86400 ))"
    if (( age_days <= KEEP_DAYS )); then
      KEEP_SET+=("${p}")
    fi
  done

  if (( KEEP_LATEST > 0 )); then
    mapfile -t newest < <(ls -1dt "${CANDIDATES[@]}" 2>/dev/null | head -n "${KEEP_LATEST}" || true)
    KEEP_SET+=("${newest[@]}")
  fi
fi

declare -A KEEP_MAP=()
for k in "${KEEP_SET[@]}"; do
  [[ -n "${k}" ]] && KEEP_MAP["${k}"]=1
done

declare -a TO_DELETE=()
for p in "${CANDIDATES[@]}"; do
  if [[ -z "${KEEP_MAP[${p}]+x}" ]]; then
    TO_DELETE+=("${p}")
  fi
done

echo "[STEP] candidate paths (outputs)"
if ((${#TO_DELETE[@]} == 0)); then
  echo "[INFO] nothing to delete in outputs by current keep policy."
else
  printf '%s\n' "${TO_DELETE[@]}"
fi

safe_remove() {
  local path="$1"
  if [[ "${path}" != "${OUTPUT_ROOT}"/* ]]; then
    echo "[SKIP] unsafe path: ${path}"
    return 0
  fi
  if [[ "${path}" == *"/models"* || "${path}" == *"/processed"* || "${path}" == "${REPO_ROOT}"* ]]; then
    echo "[SKIP] protected path: ${path}"
    return 0
  fi
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[DRY-RUN] rm -rf ${path}"
  else
    rm -rf "${path}"
    echo "[OK] removed ${path}"
  fi
}

echo "[STEP] cleanup outputs"
for p in "${TO_DELETE[@]}"; do
  safe_remove "${p}"
done

echo "[STEP] cleanup tmp project logs"
TMP_LOGS=()
while IFS= read -r f; do
  TMP_LOGS+=("${f}")
done < <(find /tmp -maxdepth 2 -type f \( -name 'streamlit_*.log' -o -name 'pangu*.log' -o -name 'forecast*.log' \) 2>/dev/null || true)

if ((${#TMP_LOGS[@]} == 0)); then
  echo "[INFO] no matching /tmp logs."
else
  printf '%s\n' "${TMP_LOGS[@]}"
  for f in "${TMP_LOGS[@]}"; do
    if [[ "${DRY_RUN}" -eq 1 ]]; then
      echo "[DRY-RUN] rm -f ${f}"
    else
      rm -f "${f}"
      echo "[OK] removed ${f}"
    fi
  done
fi

echo "[STEP] cleanup pip cache"
if command -v pip >/dev/null 2>&1; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[DRY-RUN] pip cache purge"
  else
    pip cache purge || true
  fi
else
  echo "[INFO] pip not found, skip."
fi

echo "[STEP] cleanup uv/pytest caches"
for d in "${REPO_ROOT}/.pytest_cache" "${REPO_ROOT}/.ruff_cache" "${REPO_ROOT}/.mypy_cache"; do
  if [[ -d "${d}" ]]; then
    if [[ "${DRY_RUN}" -eq 1 ]]; then
      echo "[DRY-RUN] rm -rf ${d}"
    else
      rm -rf "${d}"
      echo "[OK] removed ${d}"
    fi
  fi
done

if command -v uv >/dev/null 2>&1; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[DRY-RUN] uv cache clean"
  else
    uv cache clean || true
  fi
else
  echo "[INFO] uv not found, skip."
fi

echo "[STEP] disk usage after cleanup"
df -h || true
du -sh "${OUTPUT_ROOT}" 2>/dev/null || true
du -sh "${MODELS_ROOT_DEFAULT}" 2>/dev/null || true
du -sh "${PROCESSED_ROOT_DEFAULT}" 2>/dev/null || true

echo "[NEXT] 只看占用: bash scripts/cleanup_check.sh"
echo "[NEXT] 真清理示例: bash scripts/cleanup_autodl.sh --force --keep-latest 2 --keep-days 3"
