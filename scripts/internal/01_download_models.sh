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

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# --- SSL CA fix (AutoDL containers often lack CA certs) ---
if [[ -z "${SSL_CERT_FILE:-}" && -z "${REQUESTS_CA_BUNDLE:-}" ]]; then
  _CERTIFI_CA=""
  for _PY in "${ROOT_DIR}/.venv-gpu/bin/python" "${ROOT_DIR}/.venv-cpu/bin/python" "python3" "python"; do
    if command -v "${_PY}" >/dev/null 2>&1 || [[ -x "${_PY}" ]]; then
      _CERTIFI_CA="$("${_PY}" -c "import certifi; print(certifi.where())" 2>/dev/null || true)"
      if [[ -n "${_CERTIFI_CA}" && -f "${_CERTIFI_CA}" ]]; then break; fi
      _CERTIFI_CA=""
    fi
  done
  if [[ -n "${_CERTIFI_CA}" ]]; then
    export SSL_CERT_FILE="${_CERTIFI_CA}"
    export REQUESTS_CA_BUNDLE="${_CERTIFI_CA}"
    export CURL_CA_BUNDLE="${_CERTIFI_CA}"
  fi
  unset _CERTIFI_CA _PY
fi

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

# 记录下载失败的模型
FAILED_MODELS=()

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
    wget -c --timeout=20 --tries=3 --inet4-only ${SSL_CERT_FILE:+--ca-certificate="${SSL_CERT_FILE}"} -O "${name}.partial" "$url" || true
  elif command -v curl >/dev/null 2>&1; then
    curl -L --retry 3 --connect-timeout 20 ${SSL_CERT_FILE:+--cacert "${SSL_CERT_FILE}"} -o "${name}.partial" "$url" || true
  else
    echo "[WARN] No wget/curl found."
    FAILED_MODELS+=("${name}")
    return 1
  fi
  if [[ -f "${name}.partial" ]]; then
    mv "${name}.partial" "${name}"
  fi
  if size_ok "${name}"; then
    echo "ok (size=$(stat -c%s "${name}"))"
  else
    echo "[WARN] 下载失败或文件太小: ${name}"
    rm -f "${name}" 2>/dev/null || true
    FAILED_MODELS+=("${name}")
    return 1
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
  echo "[WARN] 下载失败: ${name}"
  FAILED_MODELS+=("${name}")
  return 1
}

if [[ "${SOURCE}" == "gdrive" ]]; then
  download_gdrive "${GID_1}" "pangu_weather_1.onnx" || true
  download_gdrive "${GID_3}" "pangu_weather_3.onnx" || true
  download_gdrive "${GID_6}" "pangu_weather_6.onnx" || true
  download_gdrive "${GID_24}" "pangu_weather_24.onnx" || true
else
  download_hf "${BASE_URL}/pangu_weather_1.onnx" "pangu_weather_1.onnx" || true
  download_hf "${BASE_URL}/pangu_weather_3.onnx" "pangu_weather_3.onnx" || true
  download_hf "${BASE_URL}/pangu_weather_6.onnx" "pangu_weather_6.onnx" || true
  download_hf "${BASE_URL}/pangu_weather_24.onnx" "pangu_weather_24.onnx" || true
fi

# ---------------------------------------------------------------------------
# 最终校验与提示
# ---------------------------------------------------------------------------
echo ""
echo "========== 模型文件状态 =========="
ALL_OK=1
for MODEL_NAME in pangu_weather_1.onnx pangu_weather_3.onnx pangu_weather_6.onnx pangu_weather_24.onnx; do
  if file_ok "${MODEL_NAME}" && size_ok "${MODEL_NAME}"; then
    echo "[OK]   ${MODEL_NAME} ($(stat -c%s "${MODEL_NAME}" | numfmt --to=iec 2>/dev/null || stat -c%s "${MODEL_NAME}"))"
  else
    echo "[MISS] ${MODEL_NAME}"
    ALL_OK=0
  fi
done
echo "==================================="

if [[ "${ALL_OK}" -eq 1 ]]; then
  echo ""
  echo "✅ 所有模型就绪"
  ls -lh *.onnx
else
  echo ""
  echo "⚠️  部分模型下载失败，请手动下载后放入: ${MODEL_DIR}/"
  echo ""
  echo "下载链接（选任一可用来源）:"
  echo ""
  echo "  HuggingFace（推荐）:"
  echo "    ${BASE_URL}/pangu_weather_1.onnx"
  echo "    ${BASE_URL}/pangu_weather_3.onnx"
  echo "    ${BASE_URL}/pangu_weather_6.onnx"
  echo "    ${BASE_URL}/pangu_weather_24.onnx"
  echo ""
  echo "  Google Drive（备选）:"
  echo "    1h:  https://drive.google.com/uc?export=download&id=${GID_1}"
  echo "    3h:  https://drive.google.com/uc?export=download&id=${GID_3}"
  echo "    6h:  https://drive.google.com/uc?export=download&id=${GID_6}"
  echo "    24h: https://drive.google.com/uc?export=download&id=${GID_24}"
  echo ""
  echo "放置完成后重新验证:"
  echo "  bash scripts/internal/01_download_models.sh --dir ${MODEL_DIR}"
  # 不 exit 2，允许后续流程继续尝试
fi
