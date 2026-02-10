#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/01_download_models.sh [--base URL] [--dir PATH] [--no-download]"
  echo "Purpose: download 1/3/6/24h ONNX models. Default source: HuggingFace."
  echo "Examples:"
  echo "  scripts/01_download_models.sh"
  echo "  scripts/01_download_models.sh --base https://huggingface.co/OpenEarthLab/Pangu-Weather/resolve/main"
  echo "  scripts/01_download_models.sh --no-download"
  exit 0
fi

MODEL_DIR="/root/autodl-tmp/pangu-weather-repro/models"
BASE_URL="https://huggingface.co/OpenEarthLab/Pangu-Weather/resolve/main"
MODE="download"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base)
      BASE_URL="$2"
      shift 2
      ;;
    --dir)
      MODEL_DIR="$2"
      shift 2
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

if [[ "${MODE}" == "nodownload" ]]; then
  echo "Manual download mode."
  echo "Place these files into: ${MODEL_DIR}"
  echo "  - pangu_weather_1.onnx"
  echo "  - pangu_weather_3.onnx"
  echo "  - pangu_weather_6.onnx"
  echo "  - pangu_weather_24.onnx"
  echo "Then set MODELS_ROOT or rerun this script."
  exit 0
fi

download() {
  local url="$1"
  local name="$2"
  if [[ -f "${name}" ]]; then
    echo "exists (skip): ${name}"
    return 0
  fi
  echo "downloading: ${name}"
  if command -v wget >/dev/null 2>&1; then
    wget -c --timeout=20 --tries=3 --inet4-only "$url"
  elif command -v curl >/dev/null 2>&1; then
    curl -L --retry 3 --connect-timeout 20 -o "$name" "$url"
  else
    echo "No wget/curl found. Download manually and place files in ${MODEL_DIR}."
    exit 1
  fi
}

download "${BASE_URL}/pangu_weather_1.onnx" "pangu_weather_1.onnx"
download "${BASE_URL}/pangu_weather_3.onnx" "pangu_weather_3.onnx"
download "${BASE_URL}/pangu_weather_6.onnx" "pangu_weather_6.onnx"
download "${BASE_URL}/pangu_weather_24.onnx" "pangu_weather_24.onnx"

echo "✅ models ready"
ls -lh
