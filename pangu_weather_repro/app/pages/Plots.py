"""Plots page for Streamlit skeleton."""
from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st
from pangu_weather_repro.app.plot_filters import parse_product_name


def _collect_pngs(base: Path) -> list[str]:
    if not base.exists():
        return []
    return sorted([str(p.relative_to(base)) for p in base.rglob("*.png")])[:200]


def _read_json_meta(product_dir: Path, rel_png: str) -> dict[str, object]:
    meta_path = product_dir / rel_png.replace(".png", ".json")
    if not meta_path.exists():
        return {}
    try:
        with open(meta_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


st.title("Plots")
root_dir = Path(__file__).resolve().parents[3]
fig_root = root_dir / "figures"
output_root = Path(os.environ.get("OUTPUT_ROOT", str(root_dir / "outputs")))

st.write("Figures root:", str(fig_root))
st.write("Output root:", str(output_root))

pngs = _collect_pngs(fig_root)
if pngs:
    st.subheader("Detected PNG Files")
    st.write(pngs[:50])
else:
    st.info("No PNG files found under figures/.")

st.subheader("Product Bundle（产品图族）")
product_dir = fig_root / "product"
product_pngs = _collect_pngs(product_dir)
if product_pngs:
    st.write("figures/product 已生成文件：")
    product_only = [p for p in product_pngs if p.startswith("product_")]
    if not product_only:
        st.write(product_pngs[:50])
    else:
        parsed = [(parse_product_name(Path(p).name), p) for p in product_only]
        kinds = sorted({k for (k, _v, _h), _p in parsed})
        vars_ = sorted({v for (_k, v, _h), _p in parsed})
        leads = sorted({h for (_k, _v, h), _p in parsed})

        col1, col2, col3 = st.columns(3)
        with col1:
            kind_sel = st.selectbox("kind", options=["all"] + kinds, index=0)
        with col2:
            var_sel = st.selectbox("var", options=["all"] + vars_, index=0)
        with col3:
            lead_sel = st.selectbox("lead", options=["all"] + leads, index=0)

        filtered = []
        for (kind, var, lead), rel in parsed:
            if kind_sel != "all" and kind != kind_sel:
                continue
            if var_sel != "all" and var != var_sel:
                continue
            if lead_sel != "all" and lead != lead_sel:
                continue
            filtered.append(rel)

        st.write(f"筛选结果：{len(filtered)} 个文件")
        st.write(filtered[:80])

        preview_rows = []
        for rel in filtered[:20]:
            meta = _read_json_meta(product_dir, rel)
            preview_rows.append(
                {
                    "file": rel,
                    "style_profile": meta.get("style_profile", ""),
                    "extent": meta.get("extent", []),
                    "with_geo": meta.get("with_geo", ""),
                }
            )
        if preview_rows:
            st.caption("元数据预览（前 20 个）")
            st.dataframe(preview_rows, use_container_width=True)

        # 根据当前筛选条件给出可复制的 CLI 模板，降低复现门槛。
        cmd_kinds = [kind_sel] if kind_sel != "all" else []
        cmd_vars = [var_sel] if var_sel != "all" else []
        cmd_hours = [lead_sel] if lead_sel != "all" else []
        kind_arg = ",".join(cmd_kinds) if cmd_kinds else "fill,diff,vector,wind_speed,msl_wind"
        var_arg = ",".join(cmd_vars) if cmd_vars else "z500,t2m,u10,v10,msl"
        hour_arg = ",".join(cmd_hours) if cmd_hours else "24,30"
        cmd = (
            'bash scripts/run_product_bundle.sh '
            '--rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" '
            f'--vars {var_arg} --hours {hour_arg} --kinds {kind_arg} --style-profile standard --force'
        )
        st.caption("可复制命令（按当前筛选生成）")
        st.code(cmd, language="bash")
        st.caption("区域图模板（可选，示例范围：95,145,10,50）")
        st.code(
            cmd.replace(" --force", " --extent 95,145,10,50 --force"),
            language="bash",
        )
else:
    st.info("figures/product 为空。")

st.code(
    "bash scripts/run_product_bundle.sh --vars z500,t2m --hours 24,30",
    language="bash",
)
