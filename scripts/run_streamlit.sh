#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/run_streamlit.sh [--host 0.0.0.0] [--port 8501] [--cpu]"
  echo "Purpose: run Streamlit app with repo PYTHONPATH and managed venv."
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="0.0.0.0"
PORT="8501"
USE_CPU="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --cpu)
      USE_CPU="1"
      shift 1
      ;;
    *)
      echo "Unknown arg: $1"
      exit 1
      ;;
  esac
done

if [[ "${USE_CPU}" == "1" ]]; then
  RUNNER="${ROOT_DIR}/scripts/run_cpu.sh"
else
  RUNNER="${ROOT_DIR}/scripts/run_gpu.sh"
fi

if [[ ! -x "${RUNNER}" ]]; then
  echo "Runner not executable: ${RUNNER}"
  echo "Next: chmod +x ${RUNNER}"
  exit 1
fi

echo "[STEP] start streamlit"
echo "[ENV] runner=${RUNNER}"
echo "[APP] ${ROOT_DIR}/pangu_weather_repro/app/app.py"
echo "[URL] http://${HOST}:${PORT}"
echo "[NEXT] Ctrl+C to stop"

"${RUNNER}" -m streamlit run "${ROOT_DIR}/pangu_weather_repro/app/app.py" --server.address "${HOST}" --server.port "${PORT}"
