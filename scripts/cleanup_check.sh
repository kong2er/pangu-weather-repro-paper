#!/usr/bin/env bash
set -euo pipefail

ROOT_TMP="/root/autodl-tmp/pangu-weather-repro"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[STEP] disk summary"
df -h || true

echo "[STEP] key directories"
du -sh "${ROOT_TMP}" 2>/dev/null || true
du -sh "${ROOT_TMP}/outputs" 2>/dev/null || true
du -sh "${ROOT_TMP}/models" 2>/dev/null || true
du -sh "${ROOT_TMP}/processed" 2>/dev/null || true
du -sh "${REPO_ROOT}" 2>/dev/null || true

echo "[STEP] top 20 in ${ROOT_TMP}"
if [[ -d "${ROOT_TMP}" ]]; then
  du -ah "${ROOT_TMP}" 2>/dev/null | sort -hr | head -n 20
else
  echo "[INFO] ${ROOT_TMP} not found."
fi

echo "[STEP] top 20 in repo"
du -ah "${REPO_ROOT}" 2>/dev/null | sort -hr | head -n 20

echo "[NEXT] 预演清理: bash scripts/cleanup_autodl.sh --dry-run"
echo "[NEXT] 真清理: bash scripts/cleanup_autodl.sh --force --keep-latest 2 --keep-days 3"
