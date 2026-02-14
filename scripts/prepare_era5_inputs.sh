#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: scripts/prepare_era5_inputs.sh [OPTIONS]

Purpose: 准备 ERA5 数据（推理输入 + 评估真值）。

选项:
  --date YYYYMMDD       初始场日期（默认 configs/default.env 中的 DATE）
  --hour HH             初始场小时（默认 configs/default.env 中的 HOUR）
  --yes                 非交互模式，跳过所有询问
  --dataset-mode MODE   default = 自动下载默认数据集 | custom = 手动放置
  --force-preprocess    强制重新预处理（即使 npy 已存在）
  --ensure-eval-gt      同时下载 Day5 RMSE 评估所需的 ERA5 真值文件
                        （根据 rollout 步长推导需要的 nc 文件）
  --eval-steps STEPS    评估真值的步长（小时），逗号分隔，默认 "24,6"
                        仅在 --ensure-eval-gt 生效时使用

功能说明:
  1) 下载 ERA5 single/pressure nc 到 ERA5_RAW_ROOT（推理输入）
  2) 预处理 nc -> PROCESSED_ROOT/{surface.npy,pressure.npy}
  3) 验证预处理输出
  4) [可选] 下载评估真值 ERA5 pressure nc（用于 Day5 RMSE）

注意:
  - 需要 ~/.cdsapirc 才能自动下载
  - 无法联网时请手动放置:
    推理输入: ERA5_RAW_ROOT/era5_single_<date><hour>.nc + era5_pressure_<date><hour>.nc
    或预处理: PROCESSED_ROOT/surface.npy + pressure.npy
    评估真值: ERA5_RAW_ROOT/era5_pressure_<date+step>.nc（每个评估步长一个文件）
  - 非交互环境中请使用 --yes
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
ENSURE_EVAL_GT=0
EVAL_STEPS="24,6"
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
    --ensure-eval-gt)
      ENSURE_EVAL_GT=1
      shift 1
      ;;
    --eval-steps)
      EVAL_STEPS="${2:?missing value for --eval-steps}"
      shift 2
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

# Guard corrupted zero-byte nc files from previous failed downloads.
if [[ -f "${SINGLE_NC}" && ! -s "${SINGLE_NC}" ]]; then
  echo "[清理] 检测到空文件，删除: ${SINGLE_NC}"
  rm -f "${SINGLE_NC}"
fi
if [[ -f "${PRESSURE_NC}" && ! -s "${PRESSURE_NC}" ]]; then
  echo "[清理] 检测到空文件，删除: ${PRESSURE_NC}"
  rm -f "${PRESSURE_NC}"
fi

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
  if [[ ! -s "${SINGLE_NC}" || ! -s "${PRESSURE_NC}" ]]; then
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
          echo "请输入 CDS API Key（支持以下任一格式）："
          echo "  1) 纯 key，例如：247b32b6-xxxx"
          echo "  2) uid:key，例如：123456:247b32b6-xxxx"
          echo "  3) key: <value>（可直接粘贴）"
          read -r -p "> " CDS_KEY_INPUT
          CDS_KEY_INPUT="${CDS_KEY_INPUT#key:}"
          CDS_KEY_INPUT="$(echo "${CDS_KEY_INPUT}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
          if [[ -z "${CDS_KEY_INPUT}" ]]; then
            echo "[失败] API Key 为空。"
            exit 1
          fi
          cat > "${HOME}/.cdsapirc" <<EOF
url: https://cds.climate.copernicus.eu/api
key: ${CDS_KEY_INPUT}
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

# ---------------------------------------------------------------------------
# 评估真值 ERA5 文件下载（Day5 RMSE 需要）
# 根据初始场时间 + 步长，推导出对应的真值时刻并下载 pressure nc
# ---------------------------------------------------------------------------
if [[ "${ENSURE_EVAL_GT}" -eq 1 ]]; then
  echo ""
  echo "[STEP] 检查/下载评估真值 ERA5 pressure 文件"

  # 用 Python 计算所需的真值时刻（避免 bash 日期计算兼容性问题）
  EVAL_GT_DATES=$("${ROOT_DIR}/scripts/run_gpu.sh" -c "
import datetime, sys
dt = datetime.datetime.strptime('${DATE_ARG}${HOUR_ARG}', '%Y%m%d%H')
steps = [int(x) for x in '${EVAL_STEPS}'.split(',')]
acc = 0
for s in steps:
    acc += s
    gt_dt = dt + datetime.timedelta(hours=acc)
    print(gt_dt.strftime('%Y%m%d%H'))
")

  GT_ALL_OK=1
  GT_DOWNLOADED=0
  GT_SKIPPED=0
  for GT_STAMP in ${EVAL_GT_DATES}; do
    GT_NC="${ERA5_RAW_ROOT}/era5_pressure_${GT_STAMP}.nc"
    if [[ -s "${GT_NC}" ]]; then
      echo "[OK] 真值文件已存在: ${GT_NC}"
      GT_SKIPPED=$((GT_SKIPPED + 1))
      continue
    fi
    # 清除空文件
    if [[ -f "${GT_NC}" && ! -s "${GT_NC}" ]]; then
      echo "[清理] 删除空文件: ${GT_NC}"
      rm -f "${GT_NC}"
    fi
    GT_DATE_PART="${GT_STAMP:0:8}"
    GT_HOUR_PART="${GT_STAMP:8:2}"
    echo "[下载] 评估真值: era5_pressure_${GT_STAMP}.nc (date=${GT_DATE_PART} hour=${GT_HOUR_PART})"
    if "${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/scripts/internal/03_download_era5_pressure.py" \
      --date "${GT_DATE_PART}" --hour "${GT_HOUR_PART}" --out-dir "${ERA5_RAW_ROOT}"; then
      if [[ -s "${GT_NC}" ]]; then
        echo "[OK] 下载成功: ${GT_NC}"
        GT_DOWNLOADED=$((GT_DOWNLOADED + 1))
      else
        echo "[WARN] 下载命令成功但文件为空或不存在: ${GT_NC}"
        GT_ALL_OK=0
      fi
    else
      echo "[WARN] 下载失败: ${GT_NC}"
      echo "[提示] 可手动放置: ${GT_NC}"
      GT_ALL_OK=0
    fi
  done

  echo ""
  echo "[评估真值] 已下载=${GT_DOWNLOADED}, 已跳过=${GT_SKIPPED}"
  if [[ "${GT_ALL_OK}" -eq 1 ]]; then
    echo "[PASS] 所有评估真值文件就绪"
  else
    echo "[WARN] 部分评估真值文件缺失，Day5 RMSE 可能回退到 npz 内嵌 gt"
    echo "[提示] 手动放置缺失文件到 ${ERA5_RAW_ROOT}/ 后重跑:"
    echo "       bash scripts/prepare_era5_inputs.sh --ensure-eval-gt --yes"
  fi
fi
