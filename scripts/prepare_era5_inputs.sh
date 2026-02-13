#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: scripts/prepare_era5_inputs.sh [--date YYYYMMDD] [--hour HH] [--yes] [--dataset-mode default|custom] [--force-preprocess]
Purpose: prepare Day3 GPU smoke inputs (surface.npy + pressure.npy).

What it does:
1) download ERA5 single/pressure nc to ERA5_RAW_ROOT
2) preprocess nc -> PROCESSED_ROOT/{surface.npy,pressure.npy}
3) validate processed inputs

Notes:
- Requires ~/.cdsapirc for CDS API download.
- If your network cannot access CDS, place nc files manually:
  ERA5_RAW_ROOT/era5_single_<date><hour>.nc
  ERA5_RAW_ROOT/era5_pressure_<date><hour>.nc
- Or place processed numpy files directly:
  PROCESSED_ROOT/surface.npy
  PROCESSED_ROOT/pressure.npy
- Interactive guard:
  yes  -> follow project default dataset and auto-download when needed
  no   -> use custom dataset and print manual-placement hints
EOF
  exit 0
fi

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/configs/default.env"

DATE_ARG="${DATE}"
HOUR_ARG="${HOUR}"
DATASET_MODE=""
ASSUME_YES=0
FORCE_PREPROCESS=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --date)
      DATE_ARG="${2:?missing value for --date}"
      shift 2
      ;;
    --hour)
      HOUR_ARG="${2:?missing value for --hour}"
      shift 2
      ;;
    --dataset-mode)
      DATASET_MODE="${2:?missing value for --dataset-mode}"
      shift 2
      ;;
    --yes)
      ASSUME_YES=1
      DATASET_MODE="default"
      shift 1
      ;;
    --force-preprocess)
      FORCE_PREPROCESS=1
      shift 1
      ;;
    *)
      echo "Unknown arg: $1"
      echo "Try: scripts/prepare_era5_inputs.sh --help"
      exit 2
      ;;
  esac
done

SINGLE_NC="${ERA5_RAW_ROOT}/era5_single_${DATE_ARG}${HOUR_ARG}.nc"
PRESSURE_NC="${ERA5_RAW_ROOT}/era5_pressure_${DATE_ARG}${HOUR_ARG}.nc"
SURFACE_NPY="${PROCESSED_ROOT}/surface.npy"
PRESSURE_NPY="${PROCESSED_ROOT}/pressure.npy"

mkdir -p "${ERA5_RAW_ROOT}" "${PROCESSED_ROOT}"

if [[ -z "${DATASET_MODE}" ]]; then
  if [[ "${ASSUME_YES}" -eq 1 ]]; then
    DATASET_MODE="default"
  elif [[ -t 0 ]]; then
    echo "[询问] 是否要自动下载默认数据集？(yes/no)"
    read -r -p "> " REPLY
    case "${REPLY}" in
      yes|y|Y)
        DATASET_MODE="default"
        ;;
      no|n|N)
        DATASET_MODE="custom"
        ;;
      *)
        echo "[失败] 请输入 yes 或 no。"
        exit 2
        ;;
    esac
  else
    DATASET_MODE="default"
  fi
fi

if [[ "${DATASET_MODE}" != "default" && "${DATASET_MODE}" != "custom" ]]; then
  echo "[FAIL] --dataset-mode must be default or custom"
  exit 2
fi

# Fast path: if processed inputs already exist, do not require nc/cdsapirc.
if [[ "${FORCE_PREPROCESS}" -eq 0 && -s "${SURFACE_NPY}" && -s "${PRESSURE_NPY}" ]]; then
  echo "[STEP] processed npy already present (skip download/preprocess)"
else
  if [[ ! -f "${SINGLE_NC}" || ! -f "${PRESSURE_NC}" ]]; then
  if [[ "${DATASET_MODE}" == "custom" ]]; then
    cat <<EOF
[提示] 请先手动添加你想要的数据集。
[建议放置路径]
- 原始 nc:
  ${SINGLE_NC}
  ${PRESSURE_NC}
- 或预处理 npy:
  ${SURFACE_NPY}
  ${PRESSURE_NPY}
[下一步] 数据放置完成后重新执行:
  bash scripts/prepare_era5_inputs.sh --dataset-mode custom
EOF
    exit 0
  fi
  if [[ ! -f "${HOME}/.cdsapirc" ]]; then
    echo "[提示] 未检测到 ~/.cdsapirc，且本地未发现可用 ERA5 数据。"
    if [[ -t 0 ]]; then
      echo "[询问] 是否现在填写 CDS API Key？(yes/no)"
      read -r -p "> " API_REPLY
      case "${API_REPLY}" in
        yes|y|Y)
          echo "请输入 CDS UID（例如 123456）："
          read -r -p "> " CDS_UID
          echo "请输入 CDS API Key："
          read -r -p "> " CDS_KEY
          if [[ -z "${CDS_UID}" || -z "${CDS_KEY}" ]]; then
            echo "[失败] UID 或 API Key 为空。"
            exit 1
          fi
          cat > "${HOME}/.cdsapirc" <<EOF
url: https://cds.climate.copernicus.eu/api
key: ${CDS_UID}:${CDS_KEY}
EOF
          chmod 600 "${HOME}/.cdsapirc"
          echo "[OK] 已写入 ~/.cdsapirc，继续下载。"
          ;;
        no|n|N)
          cat <<EOF
[提示] 请先手动添加你想要的数据集。
[建议放置路径]
- 原始 nc:
  ${SINGLE_NC}
  ${PRESSURE_NC}
- 或预处理 npy:
  ${SURFACE_NPY}
  ${PRESSURE_NPY}
EOF
          exit 0
          ;;
        *)
          echo "[失败] 请输入 yes 或 no。"
          exit 2
          ;;
      esac
    else
      cat <<EOF
[失败] 缺少 ~/.cdsapirc，且当前为非交互环境。
[处理方式]
1) 手动创建 ~/.cdsapirc 后重试；
2) 或手动放置数据：
   ${SINGLE_NC}
   ${PRESSURE_NC}
   或
   ${SURFACE_NPY}
   ${PRESSURE_NPY}
EOF
      exit 1
    fi
  fi
  echo "[STEP] download ERA5 single-level nc"
  "${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/03_download_era5_single.py" \
    --date "${DATE_ARG}" --hour "${HOUR_ARG}" --out-dir "${ERA5_RAW_ROOT}"
  echo "[STEP] download ERA5 pressure-level nc"
  "${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/03_download_era5_pressure.py" \
    --date "${DATE_ARG}" --hour "${HOUR_ARG}" --out-dir "${ERA5_RAW_ROOT}"
  else
    echo "[STEP] ERA5 nc already present (skip download)"
  fi

  echo "[STEP] preprocess ERA5 nc -> numpy"
  "${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/04_preprocess_era5_to_npy.py" \
    --date "${DATE_ARG}" --hour "${HOUR_ARG}" --raw-dir "${ERA5_RAW_ROOT}" --out-dir "${PROCESSED_ROOT}"
fi

echo "[STEP] validate processed inputs"
"${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/05_validate_inputs.py" \
  --processed-dir "${PROCESSED_ROOT}"

echo "[PASS] ERA5 inputs ready"
echo "[OUTPUT] ${PROCESSED_ROOT}/surface.npy"
echo "[OUTPUT] ${PROCESSED_ROOT}/pressure.npy"
