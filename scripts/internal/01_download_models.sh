#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/01_download_models.sh [--source hf|gdrive] [--base URL] [--dir PATH] [--force] [--no-download]"
  echo "Purpose: download 1/3/6/24h ONNX models. Default source: HuggingFace."
  echo "Examples:"
  echo "  scripts/01_download_models.sh"
  echo "  scripts/01_download_models.sh --source gdrive"
  echo "  scripts/01_download_models.sh --base https://huggingface.co/OpenEarthLab/Pangu-Weather/resolve/main"
  echo "  scripts/01_download_models.sh --no-download"
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="/root/autodl-tmp/pangu-weather-repro/models"
BASE_URL="https://huggingface.co/OpenEarthLab/Pangu-Weather/resolve/main"
SOURCE="hf"
MODE="download"
FORCE="no"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      SOURCE="$2"
      shift 2
      ;;
    --base)
      BASE_URL="$2"
      shift 2
      ;;
    --dir)
      MODEL_DIR="$2"
      shift 2
      ;;
    --force)
      FORCE="yes"
      shift 1
      ;;
    --no-download)
      MODE="nodownload"
      shift 1
      ;;
    *)
      echo "Unknown arg: $1"
      exit 1
      ;;
  esac
done

mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

GID_1="1fg5jkiN_5dHzKb-5H9Aw4MOmfILmeY-S"
GID_3="1EdoLlAXqE9iZLt9Ej9i-JW9LTJ9Jtewt"
GID_6="1a4XTktkZa5GCtjQxDJb_fNaqTAUiEJu4"
GID_24="1lweQlxcn9fG0zKNW8ne1Khr9ehRTI6HP"

echo "[STEP] download models (source=${SOURCE}, dir=${MODEL_DIR})"

if [[ "${MODE}" == "nodownload" ]]; then
  echo "Manual download mode."
  echo "Place these files into: ${MODEL_DIR}"
  echo "  - pangu_weather_1.onnx"
  echo "  - pangu_weather_3.onnx"
  echo "  - pangu_weather_6.onnx"
  echo "  - pangu_weather_24.onnx"
  echo "Google Drive file IDs:"
  echo "  1h:  ${GID_1}"
  echo "  3h:  ${GID_3}"
  echo "  6h:  ${GID_6}"
  echo "  24h: ${GID_24}"
  echo "Next: scripts/01_download_models.sh --source gdrive --force"
  exit 0
fi

file_ok() {
  local f="$1"
  if [[ -f "$f" && -s "$f" ]]; then
    return 0
  fi
  return 1
}

size_ok() {
  local f="$1"
  local size
  size=$(stat -c%s "$f" 2>/dev/null || echo 0)
  if [[ "$size" -gt 100000000 ]]; then
    return 0
  fi
  return 1
}

download_hf() {
  local url="$1"
  local name="$2"
  echo "[FILE] ${name} -> ${MODEL_DIR}/${name}"
  if file_ok "$name" && [[ "${FORCE}" != "yes" ]]; then
    echo "exists (skip)"
    return 0
  fi
  echo "downloading..."
  if command -v wget >/dev/null 2>&1; then
    wget -c --timeout=20 --tries=3 --inet4-only -O "${name}.partial" "$url" || true
  elif command -v curl >/dev/null 2>&1; then
    curl -L --retry 3 --connect-timeout 20 -o "${name}.partial" "$url" || true
  else
    echo "No wget/curl found. Download manually and place files in ${MODEL_DIR}."
    exit 1
  fi
  if [[ -f "${name}.partial" ]]; then
    mv "${name}.partial" "${name}"
  fi
  if size_ok "${name}"; then
    echo "ok (size=$(stat -c%s "${name}"))"
  else
    echo "download failed or too small: ${name}"
    echo "Next: scripts/01_download_models.sh --source ${SOURCE} --force"
    exit 2
  fi
}

download_gdrive_curl() {
  local fid="$1"
  local name="$2"
  echo "[FILE] ${name} -> ${MODEL_DIR}/${name}"
  if file_ok "$name" && [[ "${FORCE}" != "yes" ]]; then
    echo "exists (skip)"
    return 0
  fi
  local cookie="cookie_${fid}.txt"
  local tmp="${name}.partial"
  local url="https://drive.google.com/uc?export=download&id=${fid}"
  if command -v wget >/dev/null 2>&1; then
    wget --quiet --save-cookies "${cookie}" --keep-session-cookies --no-check-certificate -O - "${url}" > /tmp/gd.html || return 1
    local confirm
    confirm=$(sed -n 's/.*confirm=\\([0-9A-Za-z_]*\\).*/\\1/p' /tmp/gd.html | head -n 1)
    if [[ -z "${confirm}" ]]; then
      return 1
    fi
    wget -c --load-cookies "${cookie}" -O "${tmp}" "${url}&confirm=${confirm}" || return 1
  elif command -v curl >/dev/null 2>&1; then
    curl -c "${cookie}" -s -L "${url}" -o /tmp/gd.html || return 1
    local confirm
    confirm=$(sed -n 's/.*confirm=\\([0-9A-Za-z_]*\\).*/\\1/p' /tmp/gd.html | head -n 1)
    if [[ -z "${confirm}" ]]; then
      return 1
    fi
    curl -L -b "${cookie}" -o "${tmp}" "${url}&confirm=${confirm}" || return 1
  else
    return 1
  fi
  rm -f "${cookie}" /tmp/gd.html
  if [[ -f "${tmp}" ]]; then
    mv "${tmp}" "${name}"
  fi
  if size_ok "${name}"; then
    echo "ok (size=$(stat -c%s "${name}"))"
    return 0
  fi
  return 1
}

download_gdrive_py() {
  local fid="$1"
  local name="$2"
  echo "[FILE] ${name} -> ${MODEL_DIR}/${name}"
  if file_ok "$name" && [[ "${FORCE}" != "yes" ]]; then
    echo "exists (skip)"
    return 0
  fi
  local py="${ROOT_DIR}/.venv-gpu/bin/python"
  if [[ ! -x "${py}" ]]; then
    return 1
  fi
  "${py}" - <<'PY' "$fid" "$name"
import os, sys, requests
fid = sys.argv[1]
name = sys.argv[2]
url = "https://drive.google.com/uc?export=download&id=" + fid
session = requests.Session()
r = session.get(url, stream=True)
token = None
for k, v in r.cookies.items():
    if k.startswith("download_warning"):
        token = v
        break
if token:
    r = session.get(url + "&confirm=" + token, stream=True)
with open(name + ".partial", "wb") as f:
    for chunk in r.iter_content(1024 * 1024):
        if chunk:
            f.write(chunk)
os.replace(name + ".partial", name)
PY
  if size_ok "${name}"; then
    echo "ok (size=$(stat -c%s "${name}"))"
    return 0
  fi
  return 1
}

download_gdrive() {
  local fid="$1"
  local name="$2"
  echo "downloading..."
  if download_gdrive_curl "$fid" "$name"; then
    return 0
  fi
  if download_gdrive_py "$fid" "$name"; then
    return 0
  fi
  echo "download failed: ${name}"
  echo "Next: scripts/01_download_models.sh --source gdrive --force"
  exit 2
}

if [[ "${SOURCE}" == "gdrive" ]]; then
  download_gdrive "${GID_1}" "pangu_weather_1.onnx"
  download_gdrive "${GID_3}" "pangu_weather_3.onnx"
  download_gdrive "${GID_6}" "pangu_weather_6.onnx"
  download_gdrive "${GID_24}" "pangu_weather_24.onnx"
else
  download_hf "${BASE_URL}/pangu_weather_1.onnx" "pangu_weather_1.onnx"
  download_hf "${BASE_URL}/pangu_weather_3.onnx" "pangu_weather_3.onnx"
  download_hf "${BASE_URL}/pangu_weather_6.onnx" "pangu_weather_6.onnx"
  download_hf "${BASE_URL}/pangu_weather_24.onnx" "pangu_weather_24.onnx"
fi

echo "✅ models ready"
ls -lh
