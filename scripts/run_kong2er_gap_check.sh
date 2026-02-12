#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUT_DIR="$ROOT_DIR/artifacts/day7"
OUT_MD="$OUT_DIR/KONG2ER_GAP_RUNTIME.md"
mkdir -p "$OUT_DIR"

has() {
  local p="$1"
  [[ -e "$p" ]] && echo "true" || echo "false"
}

grep_has() {
  local p="$1"; local pat="$2"
  if [[ -f "$p" ]] && grep -qE -- "$pat" "$p"; then
    echo "true"
  else
    echo "false"
  fi
}

STREAMLIT_APP=$(has "$ROOT_DIR/pangu_weather_repro/app/app.py")
STREAMLIT_PAGES=$(ls "$ROOT_DIR/pangu_weather_repro/app/pages"/*.py >/dev/null 2>&1 && echo true || echo false)
PRODUCT_DRAW=$(has "$ROOT_DIR/pangu_weather_repro/visualization/product_draw.py")
GEO_MODULE=$(has "$ROOT_DIR/pangu_weather_repro/visualization/geo.py")
RUN_PRODUCT_ALL=$(has "$ROOT_DIR/scripts/run_product_all.sh")
RUN_E_VERIFY=$(has "$ROOT_DIR/scripts/run_e_stage_verify.sh")
KIND_VECTOR=$(grep_has "$ROOT_DIR/tools/plot_product_bundle.py" "vector")
KIND_MSL_WIND=$(grep_has "$ROOT_DIR/tools/plot_product_bundle.py" "msl_wind")
KIND_WIND_SPEED=$(grep_has "$ROOT_DIR/tools/plot_product_bundle.py" "wind_speed")
KIND_DIFF=$(grep_has "$ROOT_DIR/tools/plot_product_bundle.py" "diff")
EXTENT_ARG=$(grep_has "$ROOT_DIR/tools/plot_product_bundle.py" "--extent")
STYLE_ARG=$(grep_has "$ROOT_DIR/tools/plot_product_bundle.py" "--style-profile")
FINAL_VERIFY_E=$(grep_has "$ROOT_DIR/scripts/final_verify.sh" "with-e-stage")

cat > "$OUT_MD" <<MARK
# KONG2ER Gap Runtime Check（自动核查）

## 核查结果
- streamlit_app: $STREAMLIT_APP
- streamlit_pages: $STREAMLIT_PAGES
- product_draw_module: $PRODUCT_DRAW
- geo_module: $GEO_MODULE
- run_product_all: $RUN_PRODUCT_ALL
- run_e_stage_verify: $RUN_E_VERIFY
- kind_diff: $KIND_DIFF
- kind_vector: $KIND_VECTOR
- kind_msl_wind: $KIND_MSL_WIND
- kind_wind_speed: $KIND_WIND_SPEED
- extent_arg: $EXTENT_ARG
- style_profile_arg: $STYLE_ARG
- final_verify_e_stage: $FINAL_VERIFY_E

## 说明
- 该检查只做“能力存在性”核查，不执行重推理。
- 若某项为 false，请优先查看 docs/_internal/BLUEPRINT_EQUIV_CHECKLIST.md 与 docs/DELIVERY_SUMMARY.md 的对应阶段。

## 下一步
bash scripts/verify_repo_health.sh
bash scripts/final_verify.sh --with-e-stage --e-stage-force
MARK

echo "[STEP] kong2er gap runtime check"
echo "[OUTPUT] $OUT_MD"
echo "[NEXT] sed -n '1,200p' $OUT_MD"
