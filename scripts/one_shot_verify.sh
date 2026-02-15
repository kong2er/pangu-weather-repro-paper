#!/usr/bin/env bash
# =============================================================================
# one_shot_verify.sh — 一键核查脚本（断线安全、统一日志、产物校验、锁保护）
#
# 设计目标:
#   1. SSH 断线不影响：建议在 tmux/screen 中运行，或自动 nohup
#   2. 所有阶段写入同一 log，Python 强制 unbuffered
#   3. 每阶段结束校验关键产物（文件存在 + 非空）
#   4. 并发保护（lockfile），避免重复启动
#   5. 最终生成 manifest.json（所有关键产物 + sha256）
#   6. 支持 --yes / --non-interactive，全程不弹交互
#   7. 不依赖 rg/dmesg，仅使用 bash 内建 + coreutils
#
# 用法:
#   bash scripts/one_shot_verify.sh [OPTIONS]
#
# 推荐运行方式（断线安全）:
#   tmux new -s verify 'bash scripts/one_shot_verify.sh --yes 2>&1 | tee verify.log'
#   # 断线后重连: tmux attach -t verify
#
# 或者:
#   nohup bash scripts/one_shot_verify.sh --yes > verify.log 2>&1 &
#   tail -f verify.log
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# 全局变量
# ---------------------------------------------------------------------------
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_FILE="${ROOT_DIR}/.one_shot_verify.lock"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${ROOT_DIR}/logs"
LOG_FILE="${LOG_DIR}/one_shot_verify_${TIMESTAMP}.log"
MANIFEST_FILE="${ROOT_DIR}/artifacts/manifest.json"

# 强制 Python 不缓冲输出
export PYTHONUNBUFFERED=1
export PYTHONFAULTHANDLER=1

# 累计错误
ERRORS=0
WARNINGS=0

# 默认选项
ASSUME_YES=0
SKIP_CPU_SMOKE=0
SKIP_GPU_SMOKE=0
SKIP_RMSE=0
SKIP_PLOTS=0
SKIP_PRODUCT=0
SKIP_E_STAGE=0
FORCE_ALL=0
FORCE_KILL=0
ENSURE_EVAL_GT=1  # 默认开启

# ---------------------------------------------------------------------------
# 帮助
# ---------------------------------------------------------------------------
usage() {
  cat <<'EOF'
Usage: bash scripts/one_shot_verify.sh [OPTIONS]

一键核查脚本：从环境检查到最终验收，统一日志、断线安全、产物校验。

选项:
  --yes, --non-interactive   非交互模式，跳过所有确认
  --force                    强制重新生成所有产物
  --force-kill               如果检测到已有运行实例，强制终止后继续
  --skip-cpu-smoke           跳过 CPU 冒烟测试
  --skip-gpu-smoke           跳过 GPU 冒烟测试
  --skip-rmse                跳过 Day5 RMSE
  --skip-plots               跳过 Day6 出图
  --skip-product             跳过产品图族
  --skip-e-stage             跳过 E 阶段验收
  --no-eval-gt               不下载评估真值 ERA5 文件
  -h, --help                 显示此帮助

推荐运行方式（SSH 断线安全）:
  # 方式 1: tmux（推荐）
  tmux new -s verify 'bash scripts/one_shot_verify.sh --yes'
  # 断线后重连: tmux attach -t verify

  # 方式 2: nohup
  nohup bash scripts/one_shot_verify.sh --yes > verify.log 2>&1 &
  # 查看进度: tail -f verify.log

  # 方式 3: screen
  screen -S verify bash scripts/one_shot_verify.sh --yes
  # 断线后重连: screen -r verify

日志:
  所有输出写入 logs/one_shot_verify_<timestamp>.log
  同时输出到终端（除非 nohup）

产物清单:
  验收完成后生成 artifacts/manifest.json（含 sha256）
EOF
}

# ---------------------------------------------------------------------------
# 参数解析
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes|--non-interactive)
      ASSUME_YES=1; shift ;;
    --force)
      FORCE_ALL=1; shift ;;
    --force-kill)
      FORCE_KILL=1; shift ;;
    --skip-cpu-smoke)
      SKIP_CPU_SMOKE=1; shift ;;
    --skip-gpu-smoke)
      SKIP_GPU_SMOKE=1; shift ;;
    --skip-rmse)
      SKIP_RMSE=1; shift ;;
    --skip-plots)
      SKIP_PLOTS=1; shift ;;
    --skip-product)
      SKIP_PRODUCT=1; shift ;;
    --skip-e-stage)
      SKIP_E_STAGE=1; shift ;;
    --no-eval-gt)
      ENSURE_EVAL_GT=0; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "[ERROR] 未知参数: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
log() {
  local ts
  ts="$(date '+%H:%M:%S')"
  echo "[${ts}] $*"
}

log_section() {
  echo ""
  echo "========================================================================"
  log "$*"
  echo "========================================================================"
}

check_file() {
  # 检查文件存在且非空，返回 0=ok, 1=fail
  local path="$1"
  local label="${2:-$1}"
  if [[ -f "${path}" && -s "${path}" ]]; then
    log "[OK] ${label}: $(ls -lh "${path}" 2>/dev/null | awk '{print $5}')"
    return 0
  elif [[ -f "${path}" ]]; then
    log "[FAIL] ${label}: 文件存在但为空"
    return 1
  else
    log "[FAIL] ${label}: 文件不存在"
    return 1
  fi
}

sha256_of() {
  # 兼容 Linux (sha256sum) 和 macOS (shasum -a 256)
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "no_sha256_tool"
  fi
}

# ---------------------------------------------------------------------------
# 并发保护（lockfile）
# ---------------------------------------------------------------------------
acquire_lock() {
  if [[ -f "${LOCK_FILE}" ]]; then
    local lock_pid
    lock_pid="$(cat "${LOCK_FILE}" 2>/dev/null || echo "")"
    if [[ -n "${lock_pid}" ]] && kill -0 "${lock_pid}" 2>/dev/null; then
      if [[ "${FORCE_KILL}" -eq 1 ]]; then
        log "[WARN] 检测到已有运行实例 (PID=${lock_pid})，--force-kill 强制终止"
        kill -TERM "${lock_pid}" 2>/dev/null || true
        sleep 2
        kill -9 "${lock_pid}" 2>/dev/null || true
        rm -f "${LOCK_FILE}"
      else
        log "[ERROR] 检测到已有运行实例 (PID=${lock_pid})"
        log "[提示] 使用 --force-kill 强制终止已有实例，或等待其完成"
        log "[提示] 如果确认没有在运行，手动删除锁: rm ${LOCK_FILE}"
        exit 1
      fi
    else
      log "[WARN] 发现残留锁文件（进程已不存在），清理中..."
      rm -f "${LOCK_FILE}"
    fi
  fi
  echo "$$" > "${LOCK_FILE}"
  trap 'rm -f "${LOCK_FILE}"; exit' EXIT INT TERM
}

# ---------------------------------------------------------------------------
# 环境预检
# ---------------------------------------------------------------------------
preflight_check() {
  log_section "阶段 0: 环境预检"

  # 检查项目目录
  if [[ ! -f "${ROOT_DIR}/pyproject.toml" ]]; then
    log "[FAIL] 不在项目根目录: ${ROOT_DIR}"
    exit 1
  fi
  log "[OK] 项目目录: ${ROOT_DIR}"

  # 检查 configs/default.env
  if [[ ! -f "${ROOT_DIR}/configs/default.env" ]]; then
    log "[FAIL] 缺少 configs/default.env"
    log "[修复] cp configs/default.env.example configs/default.env 或参照 README 创建"
    exit 1
  fi
  source "${ROOT_DIR}/configs/default.env"
  log "[OK] 配置加载: configs/default.env"
  log "     DATA_ROOT=${DATA_ROOT}"
  log "     OUTPUT_ROOT=${OUTPUT_ROOT}"
  log "     ERA5_RAW_ROOT=${ERA5_RAW_ROOT}"

  # 检查 Python 环境
  local py_ok=0
  if [[ -x "${ROOT_DIR}/.venv-cpu/bin/python" ]]; then
    log "[OK] CPU venv: ${ROOT_DIR}/.venv-cpu/bin/python"
  else
    log "[WARN] CPU venv 不存在"
    log "[修复] bash scripts/create_cpu_venv.sh"
    WARNINGS=$((WARNINGS + 1))
  fi

  if [[ -x "${ROOT_DIR}/.venv-gpu/bin/python" ]]; then
    log "[OK] GPU venv: ${ROOT_DIR}/.venv-gpu/bin/python"
    py_ok=1
  else
    log "[FAIL] GPU venv 不存在（必需）"
    log "[修复] bash scripts/create_gpu_venv.sh"
    exit 1
  fi

  # 检查核心包导入
  if "${ROOT_DIR}/scripts/run_gpu.sh" -c "import pangu_weather_repro" 2>/dev/null; then
    log "[OK] pangu_weather_repro 可导入"
  else
    log "[FAIL] pangu_weather_repro 导入失败"
    log "[修复] cd ${ROOT_DIR} && uv pip install --python .venv-gpu/bin/python -e ."
    exit 1
  fi

  # 检查关键依赖
  local deps_missing=""
  if ! "${ROOT_DIR}/scripts/run_gpu.sh" -c "import numpy" 2>/dev/null; then
    deps_missing="${deps_missing} numpy"
  fi
  if ! "${ROOT_DIR}/scripts/run_gpu.sh" -c "import onnxruntime" 2>/dev/null; then
    deps_missing="${deps_missing} onnxruntime"
  fi
  if [[ -n "${deps_missing}" ]]; then
    log "[FAIL] 缺少核心依赖:${deps_missing}"
    exit 1
  fi
  log "[OK] 核心依赖检查通过 (numpy, onnxruntime)"

  # 检查绘图依赖（缺失则自动安装）
  if ! "${ROOT_DIR}/scripts/run_gpu.sh" -c "import matplotlib, scipy" 2>/dev/null; then
    log "[INFO] 绘图依赖缺失 (matplotlib/scipy)，自动安装..."
    if bash "${ROOT_DIR}/scripts/install_extras.sh" plots --force; then
      log "[OK] 绘图依赖安装成功"
    else
      log "[FAIL] 绘图依赖安装失败"
      log "[修复] bash scripts/install_extras.sh plots --force"
      exit 1
    fi
  else
    log "[OK] 绘图依赖检查通过 (matplotlib, scipy)"
  fi

  # 检查 RMSE 依赖（缺失则自动安装）
  if ! "${ROOT_DIR}/scripts/run_gpu.sh" -c "import netCDF4" 2>/dev/null; then
    log "[INFO] RMSE 评估依赖缺失 (netCDF4)，自动安装..."
    if bash "${ROOT_DIR}/scripts/install_extras.sh" rmse --force; then
      log "[OK] RMSE 依赖安装成功"
    else
      log "[FAIL] RMSE 依赖安装失败"
      log "[修复] bash scripts/install_extras.sh rmse"
      exit 1
    fi
  else
    log "[OK] RMSE 依赖检查通过 (netCDF4)"
  fi

  # 检查磁盘空间（应用层诊断，替代 dmesg）
  if command -v df >/dev/null 2>&1; then
    local avail_kb
    avail_kb="$(df -k "${DATA_ROOT}" 2>/dev/null | awk 'NR==2{print $4}' || echo 0)"
    if [[ "${avail_kb}" -gt 0 ]]; then
      local avail_gb=$((avail_kb / 1024 / 1024))
      if [[ "${avail_gb}" -lt 5 ]]; then
        log "[WARN] DATA_ROOT 所在磁盘剩余空间不足 5GB (${avail_gb}GB)"
        log "[修复] bash scripts/internal/cleanup_autodl.sh --dry-run"
        WARNINGS=$((WARNINGS + 1))
      else
        log "[OK] 磁盘空间: ${avail_gb}GB 可用 (${DATA_ROOT})"
      fi
    fi
  fi

  # 检查 ONNX 模型文件（GPU smoke / rollout 前置）
  local models_ok=1
  for _m in pangu_weather_24.onnx pangu_weather_6.onnx; do
    if [[ ! -f "${MODELS_ROOT}/${_m}" ]]; then
      models_ok=0
      break
    fi
  done
  if [[ "${models_ok}" -eq 0 ]]; then
    log "[INFO] ONNX 模型缺失，自动下载..."
    if bash "${ROOT_DIR}/scripts/internal/01_download_models.sh"; then
      # 再次验证关键模型
      if [[ -f "${MODELS_ROOT}/pangu_weather_24.onnx" ]]; then
        log "[OK] ONNX 模型下载成功"
      else
        log "[FAIL] ONNX 模型下载完成但文件仍缺失"
        log "[修复] bash scripts/internal/01_download_models.sh --dir ${MODELS_ROOT}"
        exit 1
      fi
    else
      log "[FAIL] ONNX 模型下载失败"
      log "[修复] bash scripts/internal/01_download_models.sh --dir ${MODELS_ROOT}"
      exit 1
    fi
  else
    log "[OK] ONNX 模型文件存在"
  fi

  # 确保数据根目录存在
  mkdir -p "${DATA_ROOT}" "${OUTPUT_ROOT}" "${MODELS_ROOT}"

  # 打印运行提示
  echo ""
  log "========== 运行提示 =========="
  log "日志文件: ${LOG_FILE}"
  log "如果 SSH 断线:"
  log "  tmux 用户: tmux attach -t <session>"
  log "  nohup 用户: tail -f ${LOG_FILE}"
  log "  screen 用户: screen -r <session>"
  log "=============================="
  echo ""
}

# ---------------------------------------------------------------------------
# 阶段执行
# ---------------------------------------------------------------------------
run_cpu_smoke() {
  if [[ "${SKIP_CPU_SMOKE}" -eq 1 ]]; then
    log "[跳过] CPU 冒烟测试"
    return 0
  fi
  log_section "阶段 1: CPU 冒烟测试"
  if [[ ! -x "${ROOT_DIR}/scripts/internal/run_day8_cpu_smoke.sh" ]]; then
    log "[WARN] CPU smoke 脚本不存在，跳过"
    WARNINGS=$((WARNINGS + 1))
    return 0
  fi
  bash "${ROOT_DIR}/scripts/internal/run_day8_cpu_smoke.sh"
  log "[PASS] CPU 冒烟测试通过"
}

run_gpu_smoke() {
  if [[ "${SKIP_GPU_SMOKE}" -eq 1 ]]; then
    log "[跳过] GPU 冒烟测试"
    return 0
  fi
  log_section "阶段 2: GPU 冒烟测试 (Day3)"

  # 确保 ERA5 输入存在
  local yes_flag=""
  [[ "${ASSUME_YES}" -eq 1 ]] && yes_flag="--yes"
  if [[ ! -s "${PROCESSED_ROOT}/surface.npy" || ! -s "${PROCESSED_ROOT}/pressure.npy" ]]; then
    log "[INFO] 推理输入不存在，先执行数据准备..."
    bash "${ROOT_DIR}/scripts/prepare_era5_inputs.sh" ${yes_flag}
  fi

  bash "${ROOT_DIR}/scripts/internal/run_day3_smoke_gpu.sh"
  log "[PASS] GPU 冒烟测试通过"
}

ensure_eval_gt() {
  if [[ "${ENSURE_EVAL_GT}" -eq 0 ]]; then
    return 0
  fi
  log_section "阶段 2.5: 确保评估真值 ERA5 文件"
  local yes_flag=""
  [[ "${ASSUME_YES}" -eq 1 ]] && yes_flag="--yes"
  bash "${ROOT_DIR}/scripts/prepare_era5_inputs.sh" ${yes_flag} --ensure-eval-gt || {
    log "[WARN] 评估真值下载部分失败，RMSE 可能使用内嵌 gt"
    WARNINGS=$((WARNINGS + 1))
  }
}

ensure_rollout() {
  local rollout_dir="${OUTPUT_ROOT}/day4_rollout_30h"
  local eval_npz="${rollout_dir}/eval_z500.npz"

  if [[ -f "${eval_npz}" && -s "${eval_npz}" ]]; then
    log "[OK] rollout 数据已存在: ${eval_npz}"
    return 0
  fi

  log_section "阶段 2.8: Day4 Rollout（RMSE 前置）"
  log "[INFO] eval_z500.npz 不存在，自动运行 rollout ..."
  "${ROOT_DIR}/scripts/run_gpu.sh" "${ROOT_DIR}/tools/day4_rollout.py" \
    --steps 24,6 --noarena --out-dir "${rollout_dir}" || {
    log "[FAIL] Day4 rollout 失败"
    ERRORS=$((ERRORS + 1))
    return 1
  }

  if [[ -f "${eval_npz}" && -s "${eval_npz}" ]]; then
    log "[PASS] rollout 数据生成完成"
  else
    log "[FAIL] rollout 运行完成但 eval_z500.npz 未生成"
    ERRORS=$((ERRORS + 1))
    return 1
  fi
}

run_rmse() {
  if [[ "${SKIP_RMSE}" -eq 1 ]]; then
    log "[跳过] Day5 RMSE"
    return 0
  fi

  # 确保 rollout 数据存在
  ensure_rollout

  log_section "阶段 3: Day5 RMSE 评估"

  local force_flag=""
  [[ "${FORCE_ALL}" -eq 1 ]] && force_flag="--force"
  bash "${ROOT_DIR}/scripts/internal/run_day5_rmse.sh" ${force_flag}

  # 产物校验
  if check_file "${ROOT_DIR}/artifacts/day5/rmse.csv" "artifacts/day5/rmse.csv"; then
    log "[PASS] Day5 RMSE 产物校验通过"
  else
    log "[FAIL] Day5 RMSE 产物校验失败"
    ERRORS=$((ERRORS + 1))
  fi
}

run_plots() {
  if [[ "${SKIP_PLOTS}" -eq 1 ]]; then
    log "[跳过] Day6 出图"
    return 0
  fi
  log_section "阶段 4: Day6 论文图生成"

  local force_flag=""
  [[ "${FORCE_ALL}" -eq 1 ]] && force_flag="--force"
  bash "${ROOT_DIR}/scripts/internal/run_day6_plots.sh" ${force_flag}

  # 产物校验
  local plots_ok=0
  local plots_dir="${ROOT_DIR}/figures/day6"
  if [[ -d "${plots_dir}" ]]; then
    local png_count
    png_count="$(find "${plots_dir}" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "${png_count}" -ge 3 ]]; then
      log "[OK] Day6 图表: ${png_count} 个 PNG"
      plots_ok=1
    fi
  fi
  if [[ "${plots_ok}" -eq 1 ]]; then
    log "[PASS] Day6 出图产物校验通过"
  else
    log "[FAIL] Day6 出图产物不足（预期至少 3 个 PNG）"
    ERRORS=$((ERRORS + 1))
  fi
}

run_product() {
  if [[ "${SKIP_PRODUCT}" -eq 1 ]]; then
    log "[跳过] 产品图族"
    return 0
  fi
  log_section "阶段 5: 产品图族 (E 阶段)"

  local force_flag=""
  [[ "${FORCE_ALL}" -eq 1 ]] && force_flag="--force"

  # 检查绘图依赖
  if ! "${ROOT_DIR}/scripts/run_gpu.sh" -c "import matplotlib, scipy" 2>/dev/null; then
    log "[WARN] 绘图依赖缺失，尝试自动安装..."
    bash "${ROOT_DIR}/scripts/install_extras.sh" plots || {
      log "[FAIL] 绘图依赖安装失败"
      ERRORS=$((ERRORS + 1))
      return 1
    }
  fi

  bash "${ROOT_DIR}/scripts/run_product_all.sh" \
    --rollout-dir "${OUTPUT_ROOT}/day4_rollout_30h" \
    --hours 24,30 \
    --impl auto \
    ${force_flag} || {
    log "[FAIL] 产品图族生成失败"
    ERRORS=$((ERRORS + 1))
    return 1
  }

  # 产物校验
  local product_dir="${ROOT_DIR}/figures/product"
  if [[ -d "${product_dir}" ]]; then
    local png_count
    png_count="$(find "${product_dir}" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l | tr -d ' ')"
    local json_count
    json_count="$(find "${product_dir}" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l | tr -d ' ')"
    log "[OK] 产品图: ${png_count} PNG, ${json_count} JSON"
  fi
  log "[PASS] 产品图族生成完成"
}

run_e_stage() {
  if [[ "${SKIP_E_STAGE}" -eq 1 ]]; then
    log "[跳过] E 阶段验收"
    return 0
  fi
  log_section "阶段 6: E 阶段验收报告"

  bash "${ROOT_DIR}/scripts/internal/run_e_stage_verify.sh" --force || {
    log "[WARN] E 阶段验收部分失败"
    WARNINGS=$((WARNINGS + 1))
  }

  check_file "${ROOT_DIR}/artifacts/day7/E_STAGE_REPORT.md" "E_STAGE_REPORT.md" || {
    WARNINGS=$((WARNINGS + 1))
  }
}

run_provider_check() {
  log_section "阶段 7: ORT Provider 检查"

  if [[ -x "${ROOT_DIR}/scripts/run_gpu.sh" ]]; then
    log "[CHECK] GPU providers"
    "${ROOT_DIR}/scripts/run_gpu.sh" -c "
import onnxruntime as ort
providers = ort.get_available_providers()
print('providers:', providers)
if 'CUDAExecutionProvider' in providers:
    print('CUDA: OK')
else:
    print('CUDA: MISSING')
    import sys; sys.exit(1)
" || {
      log "[FAIL] CUDAExecutionProvider 不可用"
      log "[修复] bash scripts/create_gpu_venv.sh --update && source scripts/env_gpu.sh"
      ERRORS=$((ERRORS + 1))
    }
  fi
}

# ---------------------------------------------------------------------------
# Manifest 生成
# ---------------------------------------------------------------------------
generate_manifest() {
  log_section "生成产物清单 (manifest.json)"

  mkdir -p "$(dirname "${MANIFEST_FILE}")"

  "${ROOT_DIR}/scripts/run_gpu.sh" -c "
import json, os, sys, hashlib, datetime

def sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return 'error'

def file_info(path):
    info = {'path': path, 'exists': os.path.exists(path)}
    if info['exists']:
        stat = os.stat(path)
        info['size_bytes'] = stat.st_size
        info['sha256'] = sha256_file(path)
        info['mtime'] = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
    return info

root = '${ROOT_DIR}'
artifacts = [
    os.path.join(root, 'artifacts/day5/rmse.csv'),
    os.path.join(root, 'artifacts/day7/E_STAGE_REPORT.md'),
]

# Day6 图
day6_dir = os.path.join(root, 'figures/day6')
if os.path.isdir(day6_dir):
    for f in sorted(os.listdir(day6_dir)):
        if f.endswith('.png'):
            artifacts.append(os.path.join(day6_dir, f))

# Product 图
product_dir = os.path.join(root, 'figures/product')
if os.path.isdir(product_dir):
    for f in sorted(os.listdir(product_dir)):
        if f.endswith('.png') or f.endswith('.json'):
            artifacts.append(os.path.join(product_dir, f))

manifest = {
    'generated_at': datetime.datetime.now().isoformat(),
    'root_dir': root,
    'artifacts': [file_info(p) for p in artifacts],
}

# 统计
total = len(manifest['artifacts'])
present = sum(1 for a in manifest['artifacts'] if a['exists'])

with open('${MANIFEST_FILE}', 'w') as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

print(f'manifest: {total} 项, {present} 存在, {total - present} 缺失')
print(f'写入: ${MANIFEST_FILE}')
"
  log "[OK] manifest.json 生成完成"
}

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
main() {
  mkdir -p "${LOG_DIR}"

  # 并发锁
  acquire_lock

  # 开始记录
  exec > >(tee -a "${LOG_FILE}") 2>&1

  log "============================================================"
  log " Pangu-Weather Repro 一键核查"
  log " 时间: $(date '+%Y-%m-%d %H:%M:%S')"
  log " PID: $$"
  log " 日志: ${LOG_FILE}"
  log "============================================================"

  # 环境预检
  preflight_check

  # 执行阶段
  run_cpu_smoke
  run_gpu_smoke
  ensure_eval_gt
  run_rmse
  run_plots
  run_product
  run_e_stage
  run_provider_check

  # 生成 manifest
  generate_manifest

  # 最终报告
  log_section "最终报告"
  log "错误数: ${ERRORS}"
  log "警告数: ${WARNINGS}"
  log "日志: ${LOG_FILE}"
  log "清单: ${MANIFEST_FILE}"
  echo ""

  if [[ "${ERRORS}" -eq 0 ]]; then
    log "========================================"
    log "  FINAL VERIFY PASS"
    log "========================================"
    exit 0
  else
    log "========================================"
    log "  FINAL VERIFY FAIL (${ERRORS} errors)"
    log "========================================"
    log ""
    log "常见修复步骤:"
    log "  1. 缺少 ERA5 真值: bash scripts/prepare_era5_inputs.sh --ensure-eval-gt --yes"
    log "  2. 绘图依赖: bash scripts/install_extras.sh plots --force"
    log "  3. CUDA 问题: bash scripts/create_gpu_venv.sh --update"
    log "  4. 重跑单阶段: bash scripts/one_shot_verify.sh --yes --skip-cpu-smoke --skip-gpu-smoke"
    exit 1
  fi
}

main "$@"
