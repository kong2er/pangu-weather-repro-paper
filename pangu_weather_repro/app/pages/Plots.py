"""Plots page for Streamlit skeleton."""
from __future__ import annotations

import os
import re
from pathlib import Path

import streamlit as st


def _collect_pngs(base: Path) -> list[str]:
    if not base.exists():
        return []
    return sorted([str(p.relative_to(base)) for p in base.rglob("*.png")])[:200]


def _parse_product_name(name: str) -> tuple[str, str, str]:
    # Supports:
    # - product_z500_t+024.png
    # - product_diff_z500_t+024.png
    # - product_vector_uv10_t+024.png
    # - product_msl_wind_t+024.png
    m = re.match(r"^product_(?:(diff|vector|msl_wind)_)?([a-z0-9_]+)_t\+(\d{3})\.png$", name)
    if not m:
        return ("other", "other", "other")
    kind = m.group(1) or "fill"
    var = m.group(2)
    lead = m.group(3)
    return (kind, var, lead)


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
        parsed = [(_parse_product_name(Path(p).name), p) for p in product_only]
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
else:
    st.info("figures/product 为空。")

st.code(
    "bash scripts/run_product_bundle.sh --vars z500,t2m --hours 24,30",
    language="bash",
)
